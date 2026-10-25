"""
Validation Registry: Maps FieldSpec types and semantics to deterministic validator functions.
"""

from typing import Callable, Optional
from core.models import FieldSpec, FieldType, ValidationResult
from core.validation.validators import (
    validate_aadhaar,
    validate_choice,
    validate_date,
    validate_email,
    validate_generic_text,
    validate_mobile,
    validate_name,
    validate_pin_code,
)

VALIDATOR_MAP = {
    FieldType.AADHAAR: validate_aadhaar,
    FieldType.MOBILE: validate_mobile,
    FieldType.DATE: validate_date,
    FieldType.NAME: validate_name,
    FieldType.EMAIL: validate_email,
    FieldType.CHOICE: validate_choice,
    FieldType.TEXT: validate_generic_text,
    FieldType.ADDRESS: validate_generic_text,
    FieldType.NUMBER: validate_generic_text,
}


def validate_field_value(raw_value: str, spec: FieldSpec) -> ValidationResult:
    """
    Execute deterministic validation on a field's raw answer.
    Takes into account explicit field_type as well as semantic ID hints (e.g. 'pin_code').
    """
    if not spec.required and (not raw_value or not raw_value.strip()):
        return ValidationResult(is_valid=True, normalized_value="")

    field_id_lower = spec.id.lower()
    label_lower = spec.label.lower()

    # Priority semantic overrides
    if "aadhaar" in field_id_lower or "aadhaar" in label_lower or "uid" in field_id_lower:
        return validate_aadhaar(raw_value, spec)
    if "mobile" in field_id_lower or "phone" in field_id_lower or "contact" in field_id_lower:
        return validate_mobile(raw_value, spec)
    if "pincode" in field_id_lower or "pin_code" in field_id_lower or "pin" in field_id_lower:
        return validate_pin_code(raw_value, spec)
    if "dob" in field_id_lower or "birth" in field_id_lower or "date" in field_id_lower:
        return validate_date(raw_value, spec)
    if "email" in field_id_lower:
        return validate_email(raw_value, spec)

    # Type-based dispatch
    validator = VALIDATOR_MAP.get(spec.field_type, validate_generic_text)
    return validator(raw_value, spec)
