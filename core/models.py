"""
Core Data Models (Pydantic v2).
Defines schemas for fields, values, provenance, forms, validation results, and session states.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Supported field types for deterministic extraction & validation."""
    TEXT = "text"
    NAME = "name"
    AADHAAR = "aadhaar"
    MOBILE = "mobile"
    DATE = "date"
    NUMBER = "number"
    EMAIL = "email"
    CHOICE = "choice"
    ADDRESS = "address"
    BOOLEAN = "boolean"


class FieldState(str, Enum):
    """Lifecycle states of a field during the conversational interview."""
    PENDING = "pending"
    ASKED = "asked"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"
    CONFIRMED = "confirmed"
    OPTIONAL_SKIPPED = "optional_skipped"
    EXCEPTION_RECORDED = "exception_recorded"
    NOT_APPLICABLE = "not_applicable"


class HandlingMode(str, Enum):
    """Strategy for transforming raw input to final document representation."""
    COPY_EXACTLY = "copy_exactly"
    TRANSLITERATE = "transliterate"
    TRANSLATE = "translate"
    NORMALIZE = "normalize"


class Provenance(BaseModel):
    """Audit and data provenance record for every field value."""
    raw_input: Optional[str] = None
    input_method: str = Field(default="text", description="'speech' or 'text' or 'manual_edit'")
    spoken_language: Optional[str] = None
    transcription_mode: Optional[str] = None
    handling_applied: Optional[HandlingMode] = None
    confidence_score: Optional[float] = None
    confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None


class DestinationAnchor(BaseModel):
    """Precise location anchor for populating the output document."""
    target_type: str = Field(description="'docx_cell', 'docx_placeholder', 'pdf_acroform', 'pdf_overlay'")
    # For AcroForms
    field_name: Optional[str] = None
    # For PDF overlay coordinates
    page_number: Optional[int] = 1
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    font_size: Optional[float] = 10.0
    # For DOCX
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    col_index: Optional[int] = None
    placeholder_text: Optional[str] = None


class FieldSpec(BaseModel):
    """Immutable specification of a form field extracted from the document."""
    id: str = Field(description="Stable field identifier, e.g. 'applicant_name'")
    label: str = Field(description="Original document label, e.g. 'Full Name of Applicant'")
    explanation: Dict[str, str] = Field(
        default_factory=dict,
        description="Plain-language explanation keyed by language code (hi-IN, mr-IN, ta-IN, en-IN)",
    )
    field_type: FieldType = Field(default=FieldType.TEXT)
    required: bool = Field(default=True)
    options: List[str] = Field(default_factory=list, description="Allowed choices for CHOICE fields")
    depends_on: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Condition dict e.g. {'field_id': 'marital_status', 'value': 'Married'}",
    )
    handling: HandlingMode = Field(default=HandlingMode.COPY_EXACTLY)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    anchor: Optional[DestinationAnchor] = None
    confidence: float = Field(default=1.0)
    display_order: int = Field(default=0)


class ValidationResult(BaseModel):
    """Deterministic validation outcome."""
    is_valid: bool
    normalized_value: Optional[str] = None
    error_message: Optional[str] = None
    clarification_prompt: Optional[Dict[str, str]] = None


class FieldValue(BaseModel):
    """Runtime mutable state of an individual field."""
    field_id: str
    state: FieldState = Field(default=FieldState.PENDING)
    candidate_value: Optional[str] = None
    confirmed_value: Optional[str] = None
    validation_error: Optional[str] = None
    clarification_question: Optional[str] = None
    provenance: Optional[Provenance] = None


class FormSchema(BaseModel):
    """Structured representation of an uploaded document form."""
    form_id: str
    title: str
    source_type: str = Field(description="'docx', 'pdf_acroform', 'pdf_flat', 'scanned'")
    original_filename: str
    page_count: int = 1
    fields: List[FieldSpec] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_field_by_id(self, field_id: str) -> Optional[FieldSpec]:
        for f in self.fields:
            if f.id == field_id:
                return f
        return None


class SessionStateModel(BaseModel):
    """Typed application session tracking the full workflow state."""
    session_id: str
    chosen_language: str = "hi-IN"
    current_step: str = "welcome"  # welcome, upload, summary, language, interview, review, download
    schema_model: Optional[FormSchema] = None
    field_values: Dict[str, FieldValue] = Field(default_factory=dict)
    current_field_id: Optional[str] = None
    uploaded_file_path: Optional[str] = None
    generated_file_path: Optional[str] = None
    audio_seconds_used: int = 0
    llm_calls_used: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_or_create_field_value(self, field_id: str) -> FieldValue:
        if field_id not in self.field_values:
            self.field_values[field_id] = FieldValue(field_id=field_id)
        return self.field_values[field_id]

    def all_required_confirmed(self) -> bool:
        if not self.schema_model:
            return False
        for field in self.schema_model.fields:
            if field.required:
                val = self.field_values.get(field.id)
                if not val or val.state != FieldState.CONFIRMED:
                    return False
        return True
