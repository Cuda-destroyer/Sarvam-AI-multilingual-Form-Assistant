"""
End-to-End Workflow Integration Tests.
Executes the full pipeline across all 3 MVP document types:
Upload -> FileGate -> Ingestion -> Schema -> Interview Controller -> Validation -> Generation -> Round-Trip Verification.
"""

from pathlib import Path
import pytest
from core.generation.docx_writer import DocxDocumentWriter
from core.generation.pdf_acroform_writer import PdfAcroFormWriter
from core.generation.pdf_overlay_writer import PdfOverlayWriter
from core.generation.verifier import RoundTripVerifier
from core.ingestion.schema_builder import SchemaBuilder
from core.interview.controller import InterviewController
from core.models import FieldState, SessionStateModel
from core.validation.verhoeff import calculate_verhoeff_checksum

FIXTURES_DIR = Path("tests/fixtures/forms")
E2E_TEMP_DIR = Path("temp/e2e_test_outputs")


@pytest.fixture(autouse=True)
def setup_e2e():
    E2E_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    yield
    for f in E2E_TEMP_DIR.glob("*.*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_e2e_docx_workflow():
    # 1. Ingestion
    sample_docx = FIXTURES_DIR / "college_admission_form.docx"
    builder = SchemaBuilder()
    schema = builder.build_schema(sample_docx, "college_admission_form.docx")
    assert schema.source_type == "docx"
    assert len(schema.fields) >= 6

    # 2. Session & Language
    session = SessionStateModel(
        session_id="e2e_docx_sess",
        chosen_language="hi-IN",
        schema_model=schema,
        uploaded_file_path=str(sample_docx),
    )
    controller = InterviewController(session)

    # 3. Guided Interview Q&A
    aadhaar_pfx = "78901234567"
    valid_aadhaar = f"{aadhaar_pfx}{calculate_verhoeff_checksum(aadhaar_pfx)}"

    answers = {
        "applicant_name": "Vikramaditya Rathore",
        "date_of_birth": "15/08/1997",
        "mobile_number": "9876543210",
        "aadhaar_number": valid_aadhaar,
        "email_address": "vikram@example.com",
    }

    # Step through fields
    for fid, ans in answers.items():
        if controller.get_current_field().id == fid:
            ok, msg = controller.submit_answer(ans)
            assert ok is True
            assert controller.confirm_current_answer() is True

    # 4. Generation
    out_path = E2E_TEMP_DIR / "e2e_filled_college.docx"
    writer = DocxDocumentWriter()
    writer.populate_form(sample_docx, schema, session.field_values, out_path)
    assert out_path.exists()

    # 5. Round-Trip Verification
    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, session.field_values)

    assert report.is_verified is True
    assert report.verified_fields_count >= 5
    assert len(report.missing_fields) == 0


def test_e2e_acroform_pdf_workflow():
    sample_pdf = FIXTURES_DIR / "scholarship_application_form.pdf"
    builder = SchemaBuilder()
    schema = builder.build_schema(sample_pdf, "scholarship_application_form.pdf")
    assert schema.source_type == "pdf_acroform"

    session = SessionStateModel(
        session_id="e2e_acro_sess",
        chosen_language="mr-IN",
        schema_model=schema,
        uploaded_file_path=str(sample_pdf),
    )
    controller = InterviewController(session)

    aadhaar_pfx = "89012345678"
    valid_aadhaar = f"{aadhaar_pfx}{calculate_verhoeff_checksum(aadhaar_pfx)}"

    answers = {
        "applicant_name": "Sneha Kulkarni",
        "date_of_birth": "05/12/1999",
        "mobile_number": "9822334455",
        "aadhaar_number": valid_aadhaar,
        "email_address": "sneha@example.org",
    }

    for fid, ans in answers.items():
        if controller.get_current_field() and controller.get_current_field().id == fid:
            ok, _ = controller.submit_answer(ans)
            assert ok is True
            assert controller.confirm_current_answer() is True

    out_path = E2E_TEMP_DIR / "e2e_filled_scholarship.pdf"
    writer = PdfAcroFormWriter()
    writer.populate_form(sample_pdf, schema, session.field_values, out_path)
    assert out_path.exists()

    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, session.field_values)
    assert report.is_verified is True
    assert report.verified_fields_count >= 5


def test_e2e_flat_pdf_overlay_workflow():
    sample_pdf = FIXTURES_DIR / "bank_account_opening.pdf"
    builder = SchemaBuilder()
    schema = builder.build_schema(sample_pdf, "bank_account_opening.pdf")
    assert schema.source_type == "pdf_flat"

    session = SessionStateModel(
        session_id="e2e_flat_sess",
        chosen_language="ta-IN",
        schema_model=schema,
        uploaded_file_path=str(sample_pdf),
    )
    controller = InterviewController(session)

    answers = {
        "full_name": "Karthik Subramanian",
        "date_of_birth": "22/03/1994",
        "mobile_number": "9444112233",
    }

    for fid, ans in answers.items():
        if controller.get_current_field() and controller.get_current_field().id == fid:
            ok, _ = controller.submit_answer(ans)
            assert ok is True
            assert controller.confirm_current_answer() is True

    out_path = E2E_TEMP_DIR / "e2e_filled_bank.pdf"
    writer = PdfOverlayWriter()
    writer.populate_form(sample_pdf, schema, session.field_values, out_path)
    assert out_path.exists()

    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, session.field_values)
    assert report.is_verified is True
    assert report.verified_fields_count >= 3
