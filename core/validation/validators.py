"""
Deterministic Field Validators & Normalizers.
Implements validation rules for Aadhaar, Mobile, Dates, Names, PIN, Choices, and Emails.
No LLM is allowed to bypass these deterministic rules.
"""

from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional
from core.models import FieldSpec, FieldType, ValidationResult
from core.validation.verhoeff import validate_verhoeff


def validate_aadhaar(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """
    Validate Indian Aadhaar number:
    - Strips spaces and hyphens.
    - Must be exactly 12 digits.
    - Cannot start with '0' or '1' according to UIDAI specification.
    - Must pass Verhoeff checksum.
    """
    if not raw_value or not raw_value.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Aadhaar number cannot be blank.",
            clarification_prompt={
                "en-IN": "Please enter your 12-digit Aadhaar number.",
                "hi-IN": "कृपया अपना 12 अंकों का आधार नंबर दर्ज करें।",
            },
        )

    clean_digits = re.sub(r"[\s\-]", "", raw_value.strip())

    if not clean_digits.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message="Aadhaar number must contain only numbers.",
            clarification_prompt={
                "en-IN": "Aadhaar must contain only numbers. Please enter your 12-digit number.",
                "hi-IN": "आधार नंबर में केवल अंक होने चाहिए। कृपया 12 अंक दर्ज करें।",
            },
        )

    if len(clean_digits) != 12:
        return ValidationResult(
            is_valid=False,
            error_message=f"Aadhaar number must have exactly 12 digits (you entered {len(clean_digits)}).",
            clarification_prompt={
                "en-IN": f"Aadhaar has 12 digits, but {len(clean_digits)} were entered. Please check and re-enter.",
                "hi-IN": f"आधार में 12 अंक होते हैं, लेकिन {len(clean_digits)} दर्ज किए गए। कृपया दोबारा दर्ज करें।",
            },
        )

    if clean_digits.startswith(("0", "1")):
        return ValidationResult(
            is_valid=False,
            error_message="Aadhaar numbers cannot start with 0 or 1.",
            clarification_prompt={
                "en-IN": "Invalid Aadhaar number: numbers cannot start with 0 or 1. Please re-enter.",
                "hi-IN": "अमान्य आधार नंबर: नंबर 0 या 1 से शुरू नहीं हो सकता। कृपया पुनः दर्ज करें।",
            },
        )

    if not validate_verhoeff(clean_digits):
        return ValidationResult(
            is_valid=False,
            error_message="Invalid Aadhaar checksum. Please verify the digits carefully.",
            clarification_prompt={
                "en-IN": "The Aadhaar digits do not match the official checksum. Please re-check your Aadhaar card.",
                "hi-IN": "आधार नंबर का चेकसम मेल नहीं खाता। कृपया अपने आधार कार्ड से देखकर पुनः दर्ज करें।",
            },
        )

    # Normalized representation formatted with spaces for clarity
    normalized = f"{clean_digits[0:4]} {clean_digits[4:8]} {clean_digits[8:12]}"
    return ValidationResult(is_valid=True, normalized_value=normalized)


def validate_mobile(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """
    Validate Indian Mobile number:
    - Strips spaces, dashes, +91, 0 prefixes.
    - Must be exactly 10 digits.
    - Must begin with 6, 7, 8, or 9.
    """
    if not raw_value or not raw_value.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Mobile number cannot be blank.",
            clarification_prompt={
                "en-IN": "Please enter your 10-digit mobile number.",
                "hi-IN": "कृपया अपना 10 अंकों का मोबाइल नंबर दर्ज करें।",
            },
        )

    # Clean non-digits
    digits = re.sub(r"\D", "", raw_value.strip())

    # Handle standard prefixes
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) != 10:
        return ValidationResult(
            is_valid=False,
            error_message=f"Mobile number must be 10 digits (found {len(digits)} digits).",
            clarification_prompt={
                "en-IN": f"A valid mobile number has 10 digits. You entered {len(digits)}. Please re-enter.",
                "hi-IN": f"मोबाइल नंबर 10 अंकों का होना चाहिए। आपने {len(digits)} दर्ज किए हैं। कृपया दोबारा दर्ज करें।",
            },
        )

    if digits[0] not in {"6", "7", "8", "9"}:
        return ValidationResult(
            is_valid=False,
            error_message="Indian mobile numbers must start with 6, 7, 8, or 9.",
            clarification_prompt={
                "en-IN": "Mobile numbers in India start with 6, 7, 8, or 9. Please check and re-enter.",
                "hi-IN": "भारतीय मोबाइल नंबर 6, 7, 8 या 9 से शुरू होते हैं। कृपया सही नंबर दर्ज करें।",
            },
        )

    return ValidationResult(is_valid=True, normalized_value=digits)


def validate_date(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """
    Validate Date (e.g., Date of Birth):
    - Parses common Indian and ISO formats.
    - Validates calendar dates (e.g. Feb 30 rejected).
    - If spec is DOB, rejects future dates.
    - Standardizes to DD/MM/YYYY.
    """
    if not raw_value or not raw_value.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Date cannot be blank.",
            clarification_prompt={
                "en-IN": "Please provide the date (DD/MM/YYYY).",
                "hi-IN": "कृपया दिनांक (दिन/माह/वर्ष) प्रदान करें।",
            },
        )

    text = raw_value.strip()

    # Supported date parsing formats
    date_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    parsed_date = None
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        # Check if digits-only string like 15081995
        clean_num = re.sub(r"\D", "", text)
        if len(clean_num) == 8:
            try:
                day = int(clean_num[0:2])
                month = int(clean_num[2:4])
                year = int(clean_num[4:8])
                parsed_date = date(year, month, day)
            except ValueError:
                pass

    if not parsed_date:
        return ValidationResult(
            is_valid=False,
            error_message="Could not recognize date. Please enter in DD/MM/YYYY format.",
            clarification_prompt={
                "en-IN": "Please enter the date clearly in DD/MM/YYYY format (e.g. 15/08/1995).",
                "hi-IN": "कृपया दिनांक DD/MM/YYYY प्रारूप में स्पष्ट रूप से दर्ज करें (उदा. 15/08/1995)।",
            },
        )

    # If it is a birth date, reject future dates or > 120 years ago
    today = date.today()
    is_dob = spec and ("birth" in spec.id.lower() or "dob" in spec.id.lower())
    if is_dob:
        if parsed_date > today:
            return ValidationResult(
                is_valid=False,
                error_message="Date of birth cannot be in the future.",
                clarification_prompt={
                    "en-IN": "Date of birth cannot be in the future. Please check the year.",
                    "hi-IN": "जन्म तिथि भविष्य की नहीं हो सकती। कृपया वर्ष की जांच करें।",
                },
            )
        if (today.year - parsed_date.year) > 120:
            return ValidationResult(
                is_valid=False,
                error_message="Please verify birth year (unusually high age).",
                clarification_prompt={
                    "en-IN": "The birth year seems too old. Please confirm or re-enter.",
                    "hi-IN": "जन्म वर्ष असामान्य लग रहा है। कृपया पुष्टि करें या दोबारा दर्ज करें।",
                },
            )

    normalized = parsed_date.strftime("%d/%m/%Y")
    return ValidationResult(is_valid=True, normalized_value=normalized)


def validate_pin_code(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """Validate 6-digit Indian PIN code."""
    if not raw_value or not raw_value.strip():
        return ValidationResult(is_valid=False, error_message="PIN code cannot be blank.")

    digits = re.sub(r"\D", "", raw_value.strip())
    if len(digits) != 6:
        return ValidationResult(
            is_valid=False,
            error_message=f"PIN code must be exactly 6 digits (got {len(digits)}).",
            clarification_prompt={
                "en-IN": "Postal PIN code must be 6 digits. Please re-enter.",
                "hi-IN": "पिन कोड 6 अंकों का होना चाहिए। कृपया पुनः दर्ज करें।",
            },
        )

    if digits.startswith("0"):
        return ValidationResult(
            is_valid=False,
            error_message="Indian PIN codes cannot start with 0.",
        )

    return ValidationResult(is_valid=True, normalized_value=digits)


def validate_email(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """Validate email address format."""
    if not raw_value or not raw_value.strip():
        return ValidationResult(is_valid=False, error_message="Email cannot be blank.")

    clean_email = raw_value.strip().lower()
    email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    if not email_regex.match(clean_email):
        return ValidationResult(
            is_valid=False,
            error_message="Invalid email address format (e.g. name@example.com).",
            clarification_prompt={
                "en-IN": "Please provide a valid email address like name@example.com.",
                "hi-IN": "कृपया सही ईमेल पता दर्ज करें जैसे name@example.com.",
            },
        )

    return ValidationResult(is_valid=True, normalized_value=clean_email)


def validate_choice(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """
    Validate multiple-choice or radio options.
    Must map strictly to allowed options defined in spec.options.
    """
    if not spec or not spec.options:
        return ValidationResult(is_valid=True, normalized_value=raw_value.strip())

    input_clean = raw_value.strip().lower()

    # Exact case-insensitive match
    for opt in spec.options:
        if input_clean == opt.strip().lower():
            return ValidationResult(is_valid=True, normalized_value=opt.strip())

    # Partial / substring match if clear
    matched = [opt for opt in spec.options if input_clean in opt.lower() or opt.lower() in input_clean]
    if len(matched) == 1:
        return ValidationResult(is_valid=True, normalized_value=matched[0].strip())

    options_str = ", ".join(spec.options)
    return ValidationResult(
        is_valid=False,
        error_message=f"Please choose from available options: {options_str}",
        clarification_prompt={
            "en-IN": f"Please choose one of: {options_str}",
            "hi-IN": f"कृपया इनमें से एक विकल्प चुनें: {options_str}",
        },
    )


def validate_name(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """Validate name field (alphabetic, spaces, dots for initials)."""
    if not raw_value or not raw_value.strip():
        return ValidationResult(is_valid=False, error_message="Name cannot be blank.")

    cleaned = " ".join(raw_value.strip().split())
    # Reject strings with numbers or special symbols other than . and '
    if re.search(r"[\d@#$%^&*()_+={}\[\]:;\"<>?/\\|~`]", cleaned):
        return ValidationResult(
            is_valid=False,
            error_message="Names should only contain letters, spaces, and dots for initials.",
            clarification_prompt={
                "en-IN": "A name should not contain numbers or special characters. Please re-enter.",
                "hi-IN": "नाम में अंक या विशेष वर्ण नहीं होने चाहिए। कृपया नाम पुनः दर्ज करें।",
            },
        )

    return ValidationResult(is_valid=True, normalized_value=cleaned.title())


def validate_generic_text(raw_value: str, spec: Optional[FieldSpec] = None) -> ValidationResult:
    """Validate generic text input."""
    if not raw_value or not raw_value.strip():
        return ValidationResult(is_valid=False, error_message="This field cannot be empty.")

    cleaned = " ".join(raw_value.strip().split())
    return ValidationResult(is_valid=True, normalized_value=cleaned)
