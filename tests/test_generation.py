"""
Unit tests for Document Generation & Round-Trip Output Verification.
Tests DOCX, AcroForm PDF, and Flat PDF overlay generation with round-trip proof.
"""

from pathlib import Path
import pytest
from core.generation.docx_writer import DocxDocumentWriter
from core.generation.pdf_acroform_writer import PdfAcroFormWriter
from core.generation.pdf_overlay_writer import PdfOverlayWriter
from core.generation.verifier import RoundTripVerifier
from core.ingestion.schema_builder import SchemaBuilder
from core.models import FieldState, FieldValue

FIXTURES_DIR = Path("tests/fixtures/forms")
TEST_OUTPUTS_DIR = Path("temp/test_outputs")


@pytest.fixture(autouse=True)
def setup_dirs():
    TEST_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup generated test outputs
    for f in TEST_OUTPUTS_DIR.glob("*.*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_docx_generation_and_roundtrip_verification():
    template_path = FIXTURES_DIR / "college_admission_form.docx"
    builder = SchemaBuilder()
    schema = builder.build_schema(template_path, "college_admission_form.docx")

    # Set confirmed values
    values = {}
    test_data = {
        "applicant_name": "Rohan Sharma",
        "date_of_birth": "12/04/1998",
        "mobile_number": "9876543210",
        "aadhaar_number": "2345 6789 0123",
    }
    for field in schema.fields:
        if field.id in test_data:
            val = FieldValue(
                field_id=field.id,
                state=FieldState.CONFIRMED,
                confirmed_value=test_data[field.id],
            )
            values[field.id] = val

    out_path = TEST_OUTPUTS_DIR / "test_filled.docx"
    writer = DocxDocumentWriter()
    writer.populate_form(template_path, schema, values, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0

    # Round-trip verification
    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, values)

    assert report.is_verified is True
    assert report.total_confirmed_fields == len(test_data)
    assert report.verified_fields_count == len(test_data)
    assert len(report.missing_fields) == 0


def test_acroform_pdf_generation_and_roundtrip_verification():
    template_path = FIXTURES_DIR / "scholarship_application_form.pdf"
    builder = SchemaBuilder()
    schema = builder.build_schema(template_path, "scholarship_application_form.pdf")

    values = {}
    test_data = {
        "applicant_name": "Pooja Patil",
        "date_of_birth": "24/07/2000",
        "mobile_number": "9823456789",
        "aadhaar_number": "3456 7890 1234",
    }
    for field in schema.fields:
        if field.id in test_data:
            values[field.id] = FieldValue(
                field_id=field.id,
                state=FieldState.CONFIRMED,
                confirmed_value=test_data[field.id],
            )

    out_path = TEST_OUTPUTS_DIR / "test_filled_acro.pdf"
    writer = PdfAcroFormWriter()
    writer.populate_form(template_path, schema, values, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0

    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, values)

    assert report.is_verified is True
    assert report.total_confirmed_fields == len(test_data)
    assert report.verified_fields_count == len(test_data)


def test_flat_pdf_overlay_generation_and_roundtrip_verification():
    template_path = FIXTURES_DIR / "bank_account_opening.pdf"
    builder = SchemaBuilder()
    schema = builder.build_schema(template_path, "bank_account_opening.pdf")

    values = {}
    test_data = {
        "full_name": "Suresh Raina",
        "date_of_birth": "27/11/1986",
        "mobile_number": "9811223344",
    }
    for field in schema.fields:
        if field.id in test_data:
            values[field.id] = FieldValue(
                field_id=field.id,
                state=FieldState.CONFIRMED,
                confirmed_value=test_data[field.id],
            )

    out_path = TEST_OUTPUTS_DIR / "test_filled_flat.pdf"
    writer = PdfOverlayWriter()
    writer.populate_form(template_path, schema, values, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0

    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, values)

    assert report.is_verified is True
    assert report.total_confirmed_fields == len(test_data)
    assert report.verified_fields_count == len(test_data)
