"""
Unit tests for Conversational Interview Controller & State Machine.
"""

from pathlib import Path
import pytest
from core.ingestion.docx_reader import DocxFormReader
from core.ingestion.schema_builder import SchemaBuilder
from core.interview.controller import InterviewController
from core.models import FieldSpec, FieldState, FieldType, FormSchema, SessionStateModel
from core.validation.verhoeff import calculate_verhoeff_checksum


@pytest.fixture
def mock_session():
    # Build a simple test form schema
    prefix = "45678901234"
    valid_aadhaar = f"{prefix}{calculate_verhoeff_checksum(prefix)}"

    fields = [
        FieldSpec(id="full_name", label="Full Name", field_type=FieldType.NAME, required=True),
        FieldSpec(id="aadhaar_num", label="Aadhaar Number", field_type=FieldType.AADHAAR, required=True),
        FieldSpec(id="optional_phone", label="Alternate Phone", field_type=FieldType.MOBILE, required=False),
    ]
    schema = FormSchema(
        form_id="test_form_1",
        title="Test Admission Form",
        source_type="docx",
        original_filename="test.docx",
        fields=fields,
    )
    session = SessionStateModel(
        session_id="session_test_123",
        chosen_language="hi-IN",
        schema_model=schema,
    )
    return session, valid_aadhaar


def test_interview_flow_progression(mock_session):
    session, valid_aadhaar = mock_session
    controller = InterviewController(session)

    # 1. Starts on first field: full_name
    curr = controller.get_current_field()
    assert curr is not None
    assert curr.id == "full_name"
    assert controller.is_interview_complete() is False

    # 2. Submit valid name
    ok, msg = controller.submit_answer("Rajesh Kumar Sharma")
    assert ok is True
    val = controller.get_current_value()
    assert val.state == FieldState.AWAITING_CONFIRMATION
    assert val.candidate_value == "Rajesh Kumar Sharma"

    # 3. Confirm name -> advances to aadhaar_num
    confirmed = controller.confirm_current_answer()
    assert confirmed is True
    assert val.state == FieldState.CONFIRMED

    curr = controller.get_current_field()
    assert curr.id == "aadhaar_num"

    # 4. Try submitting invalid Aadhaar (wrong length)
    ok, err_msg = controller.submit_answer("12345")
    assert ok is False
    val = controller.get_current_value()
    assert val.state == FieldState.INVALID
    # Must remain on aadhaar_num, cannot advance
    assert controller.get_current_field().id == "aadhaar_num"

    # 5. Submit valid Aadhaar
    ok, msg = controller.submit_answer(valid_aadhaar)
    assert ok is True
    val = controller.get_current_value()
    assert val.state == FieldState.AWAITING_CONFIRMATION

    # Confirm Aadhaar -> advances to optional_phone
    assert controller.confirm_current_answer() is True
    curr = controller.get_current_field()
    assert curr.id == "optional_phone"

    # 6. Skip optional field
    assert controller.skip_optional_field() is True
    val = session.field_values["optional_phone"]
    assert val.state == FieldState.OPTIONAL_SKIPPED

    # 7. Check interview complete
    assert controller.is_interview_complete() is True
    completed, total = controller.get_progress()
    assert completed == 3
    assert total == 3


def test_cannot_skip_required_field(mock_session):
    session, _ = mock_session
    controller = InterviewController(session)
    assert controller.get_current_field().required is True

    # Trying to skip required field must fail
    assert controller.skip_optional_field() is False
    assert controller.get_current_value().state == FieldState.INVALID


def test_navigation_and_correction(mock_session):
    session, valid_aadhaar = mock_session
    controller = InterviewController(session)

    # Complete name
    controller.submit_answer("Aarav Patel")
    controller.confirm_current_answer()

    # We are now on Aadhaar
    assert controller.get_current_field().id == "aadhaar_num"

    # User realizes typo in name and navigates back
    assert controller.go_to_field("full_name") is True
    assert controller.get_current_field().id == "full_name"

    # Re-answer and confirm
    controller.submit_answer("Aarav Suresh Patel")
    controller.confirm_current_answer()

    assert session.field_values["full_name"].confirmed_value == "Aarav Suresh Patel"
    # Should advance to unresolved Aadhaar field
    assert controller.get_current_field().id == "aadhaar_num"
