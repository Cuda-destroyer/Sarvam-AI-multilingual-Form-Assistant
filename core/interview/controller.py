"""
Conversational Interview State Machine & Controller.
Coordinates the one-question-at-a-time interview flow, answer interpretation,
deterministic validation, read-back confirmations, and provenance tracking.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from core.models import (
    FieldSpec,
    FieldState,
    FieldType,
    FieldValue,
    FormSchema,
    HandlingMode,
    Provenance,
    SessionStateModel,
)
from core.privacy.logger import get_logger
from core.services.sarvam.llm import LLMService
from core.services.sarvam.speech_lang import SpeechLanguageService
from core.validation.registry import validate_field_value

logger = get_logger("interview_controller")


class InterviewController:
    """Manages the lifecycle and state transitions for a form-filling session."""

    def __init__(
        self,
        session: SessionStateModel,
        llm_service: Optional[LLMService] = None,
        speech_lang_service: Optional[SpeechLanguageService] = None,
    ):
        self.session = session
        self.schema = session.schema_model
        self.llm_service = llm_service or LLMService()
        self.speech_lang_service = speech_lang_service or SpeechLanguageService()

        # Initialize current field if not set
        if not self.session.current_field_id and self.schema and self.schema.fields:
            self.session.current_field_id = self.schema.fields[0].id

    def get_current_field(self) -> Optional[FieldSpec]:
        """Retrieve FieldSpec for current question."""
        if not self.schema or not self.session.current_field_id:
            return None
        return self.schema.get_field_by_id(self.session.current_field_id)

    def get_current_value(self) -> Optional[FieldValue]:
        """Retrieve runtime FieldValue for current question."""
        if not self.session.current_field_id:
            return None
        return self.session.get_or_create_field_value(self.session.current_field_id)

    def get_question_prompt(self, field: Optional[FieldSpec] = None) -> str:
        """Get translated question explanation in the user's chosen language."""
        f = field or self.get_current_field()
        if not f:
            return ""
        lang = self.session.chosen_language
        return self.llm_service.generate_question_prompt(f, lang)

    def submit_answer(self, raw_input: str, input_method: str = "text") -> Tuple[bool, str]:
        """
        Submit a raw answer (spoken or typed).
        1. Transforms/interprets answer.
        2. Applies deterministic validation.
        3. Updates state to AWAITING_CONFIRMATION if valid, or INVALID if rejected.
        
        Returns:
            Tuple of (is_valid, user_message)
        """
        current_spec = self.get_current_field()
        current_val = self.get_current_value()

        if not current_spec or not current_val:
            return False, "No active field found."

        raw_trimmed = raw_input.strip()
        if not raw_trimmed:
            current_val.state = FieldState.INVALID
            current_val.validation_error = "Answer cannot be empty."
            return False, "Answer cannot be empty. Please provide your response."

        # Step A: Natural Language Candidate Extraction (if complex text / speech)
        candidate = raw_trimmed
        # For non-numeric text or sentences, use LLM or transliteration
        if current_spec.field_type in (FieldType.TEXT, FieldType.ADDRESS):
            # Check if translation is needed to English
            if current_spec.handling == HandlingMode.TRANSLATE and self.session.chosen_language != "en-IN":
                candidate = self.speech_lang_service.translate_to_english(
                    raw_trimmed,
                    self.session.chosen_language,
                )
            else:
                interp = self.llm_service.interpret_answer(raw_trimmed, current_spec, self.session.chosen_language)
                candidate = interp.get("candidate_value") or raw_trimmed

        elif current_spec.field_type == FieldType.NAME:
            if current_spec.handling == HandlingMode.TRANSLITERATE and self.session.chosen_language != "en-IN":
                candidate = self.speech_lang_service.transliterate_to_latin(
                    raw_trimmed,
                    self.session.chosen_language,
                )

        # Step B: Deterministic Validation
        validation_res = validate_field_value(candidate, current_spec)

        if not validation_res.is_valid:
            current_val.state = FieldState.INVALID
            current_val.validation_error = validation_res.error_message
            prompt_lang = validation_res.clarification_prompt.get(self.session.chosen_language) if validation_res.clarification_prompt else None
            msg = prompt_lang or validation_res.error_message or "Invalid response. Please re-enter."
            current_val.clarification_question = msg
            logger.info("Validation rejected for field '%s': %s", current_spec.id, validation_res.error_message)
            return False, msg

        # Step C: Set awaiting confirmation
        current_val.candidate_value = validation_res.normalized_value or candidate
        current_val.state = FieldState.AWAITING_CONFIRMATION
        current_val.validation_error = None
        current_val.clarification_question = None

        # Build initial provenance
        current_val.provenance = Provenance(
            raw_input=raw_trimmed,
            input_method=input_method,
            spoken_language=self.session.chosen_language,
            handling_applied=current_spec.handling,
            confidence_score=1.0,
        )

        logger.info("Field '%s' valid candidate: '%s'. Awaiting user confirmation.", current_spec.id, current_val.candidate_value)
        return True, "Value accepted. Please review and confirm."

    def confirm_current_answer(self, user_confirmed_value: Optional[str] = None) -> bool:
        """
        User explicitly confirms the value.
        Advances state to CONFIRMED and proceeds to next unresolved field.
        """
        current_spec = self.get_current_field()
        current_val = self.get_current_value()

        if not current_spec or not current_val:
            return False

        final_val = user_confirmed_value or current_val.candidate_value
        if not final_val:
            return False

        # Re-verify through deterministic validator in case user edited in-place
        val_res = validate_field_value(final_val, current_spec)
        if not val_res.is_valid:
            current_val.state = FieldState.INVALID
            current_val.validation_error = val_res.error_message
            return False

        current_val.confirmed_value = val_res.normalized_value or final_val
        current_val.candidate_value = current_val.confirmed_value
        current_val.state = FieldState.CONFIRMED
        current_val.validation_error = None

        if current_val.provenance:
            current_val.provenance.confirmed_at = datetime.now(timezone.utc)
        else:
            current_val.provenance = Provenance(
                raw_input=current_val.confirmed_value,
                input_method="text",
                confirmed_at=datetime.now(timezone.utc),
            )

        logger.info("Field '%s' confirmed: '%s'.", current_spec.id, current_val.confirmed_value)

        # Move to next field
        self.advance_to_next_field()
        return True

    def skip_optional_field(self) -> bool:
        """Skip current field if it is optional."""
        current_spec = self.get_current_field()
        current_val = self.get_current_value()

        if not current_spec or not current_val:
            return False

        if current_spec.required:
            current_val.state = FieldState.INVALID
            current_val.validation_error = "This field is mandatory and cannot be skipped."
            return False

        current_val.state = FieldState.OPTIONAL_SKIPPED
        current_val.confirmed_value = ""
        logger.info("Optional field '%s' skipped by user.", current_spec.id)
        self.advance_to_next_field()
        return True

    def advance_to_next_field(self) -> Optional[str]:
        """Find and set the next unresolved field in order."""
        if not self.schema:
            return None

        for field in self.schema.fields:
            val = self.session.field_values.get(field.id)
            if not val or val.state in (FieldState.PENDING, FieldState.INVALID, FieldState.AMBIGUOUS):
                self.session.current_field_id = field.id
                return field.id

        # All fields resolved
        return None

    def go_to_field(self, field_id: str) -> bool:
        """Navigate back to a previous field for correction."""
        if not self.schema or not self.schema.get_field_by_id(field_id):
            return False

        self.session.current_field_id = field_id
        val = self.session.get_or_create_field_value(field_id)
        # If was confirmed, set back to asked/awaiting_confirmation so user can re-confirm
        if val.state == FieldState.CONFIRMED:
            val.state = FieldState.AWAITING_CONFIRMATION
        logger.info("Navigated to field '%s' for review/edit.", field_id)
        return True

    def get_progress(self) -> Tuple[int, int]:
        """Return (completed_fields_count, total_fields_count)."""
        if not self.schema or not self.schema.fields:
            return 0, 0

        total = len(self.schema.fields)
        completed = sum(
            1 for f in self.schema.fields
            if self.session.field_values.get(f.id) and self.session.field_values[f.id].state in (
                FieldState.CONFIRMED, FieldState.OPTIONAL_SKIPPED, FieldState.NOT_APPLICABLE
            )
        )
        return completed, total

    def is_interview_complete(self) -> bool:
        """Check if all mandatory fields are confirmed."""
        if not self.schema:
            return False

        for f in self.schema.fields:
            val = self.session.field_values.get(f.id)
            if f.required:
                if not val or val.state != FieldState.CONFIRMED:
                    return False
            else:
                if val and val.state not in (FieldState.CONFIRMED, FieldState.OPTIONAL_SKIPPED, FieldState.PENDING):
                    return False
        return True
