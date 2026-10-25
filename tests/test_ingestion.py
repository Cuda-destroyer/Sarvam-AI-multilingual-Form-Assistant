"""
Unit tests for Document Ingestion Pipeline:
- FileGate security & validation
- DOCX extraction
- AcroForm PDF extraction
- Flat-text PDF coordinate extraction
- Unified SchemaBuilder
"""

from pathlib import Path
import pytest
from core.ingestion.docx_reader import DocxFormReader
from core.ingestion.file_gate import DocumentFileGate, FileGateError
from core.ingestion.pdf_acroform import PdfAcroFormReader
from core.ingestion.pdf_text import PdfTextExtractor
from core.ingestion.schema_builder import SchemaBuilder
from core.models import FieldType

FIXTURES_DIR = Path("tests/fixtures/forms")


def test_file_gate_valid_documents():
    gate = DocumentFileGate()

    # DOCX
    docx_path = FIXTURES_DIR / "college_admission_form.docx"
    fmt, pages = gate.validate_file(docx_path, "college_admission_form.docx")
    assert fmt == "docx"
    assert pages >= 1

    # Flat PDF
    pdf_path = FIXTURES_DIR / "bank_account_opening.pdf"
    fmt, pages = gate.validate_file(pdf_path, "bank_account_opening.pdf")
    assert fmt == "pdf"
    assert pages == 1


def test_file_gate_rejections():
    gate = DocumentFileGate()

    # Unsupported extension
    with pytest.raises(FileGateError, match="Unsupported file format"):
        gate.validate_file(b"test", "malicious_script.exe")

    # Empty file
    with pytest.raises(FileGateError, match="empty"):
        gate.validate_file(b"", "empty.pdf")

    # Invalid PDF magic bytes
    with pytest.raises(FileGateError, match="invalid file header"):
        gate.validate_file(b"NOT_A_PDF_CONTENT", "fake.pdf")


def test_docx_reader_extraction():
    reader = DocxFormReader()
    docx_path = FIXTURES_DIR / "college_admission_form.docx"
    fields = reader.extract_fields(docx_path)

    assert len(fields) >= 6
    labels = [f.label for f in fields]
    assert "Applicant Name" in labels
    assert "Aadhaar Number" in labels
    assert "Mobile Number" in labels

    # Check that anchors are populated
    for f in fields:
        assert f.anchor is not None
        assert f.anchor.target_type in ("docx_cell", "docx_placeholder")


def test_acroform_reader_extraction():
    reader = PdfAcroFormReader()
    pdf_path = FIXTURES_DIR / "scholarship_application_form.pdf"

    assert reader.is_acroform(pdf_path) is True
    fields = reader.extract_fields(pdf_path)

    assert len(fields) >= 5
    field_ids = [f.id for f in fields]
    assert any("applicant" in fid for fid in field_ids)
    assert any("aadhaar" in fid for fid in field_ids)

    for f in fields:
        assert f.anchor is not None
        assert f.anchor.target_type == "pdf_acroform"
        assert f.anchor.field_name is not None


def test_pdf_text_extractor():
    extractor = PdfTextExtractor()
    pdf_path = FIXTURES_DIR / "bank_account_opening.pdf"
    fields = extractor.extract_fields(pdf_path)

    assert len(fields) >= 5
    labels = [f.label for f in fields]
    assert any("Full Name" in lbl for lbl in labels)
    assert any("Aadhaar" in lbl for lbl in labels)

    for f in fields:
        assert f.anchor is not None
        assert f.anchor.target_type == "pdf_overlay"
        assert f.anchor.x is not None
        assert f.anchor.y is not None


def test_schema_builder_multilingual_enrichment():
    builder = SchemaBuilder()
    docx_path = FIXTURES_DIR / "college_admission_form.docx"
    schema = builder.build_schema(docx_path, "college_admission_form.docx")

    assert schema.source_type == "docx"
    assert len(schema.fields) >= 6

    # Verify multilingual explanations exist for every field
    for field in schema.fields:
        assert "hi-IN" in field.explanation
        assert "en-IN" in field.explanation
        assert len(field.explanation["hi-IN"]) > 0
