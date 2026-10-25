"""
Unit tests for deterministic validators and Verhoeff checksum.
"""

from datetime import date, timedelta
import pytest
from core.models import FieldSpec, FieldType
from core.validation.registry import validate_field_value
from core.validation.validators import (
    validate_aadhaar,
    validate_choice,
    validate_date,
    validate_mobile,
    validate_name,
    validate_pin_code,
)
from core.validation.verhoeff import calculate_verhoeff_checksum, validate_verhoeff


def test_verhoeff_calculation_and_validation():
    # Example 11-digit prefix
    prefix = "23456789012"
    checksum = calculate_verhoeff_checksum(prefix)
    full_number = f"{prefix}{checksum}"
    assert validate_verhoeff(full_number) is True

    # Mutated digit should fail
    corrupted = f"{prefix}{(checksum + 1) % 10}"
    assert validate_verhoeff(corrupted) is False


def test_validate_aadhaar():
    # Generate a valid 12-digit Aadhaar for testing
    prefix = "34567890123"
    checksum = calculate_verhoeff_checksum(prefix)
    valid_aadhaar = f"{prefix}{checksum}"

    res = validate_aadhaar(valid_aadhaar)
    assert res.is_valid is True
    assert res.normalized_value == f"{prefix[0:4]} {prefix[4:8]} {prefix[8:11]}{checksum}"

    # Invalid: non-numeric
    assert validate_aadhaar("34567890123a").is_valid is False

    # Invalid: 11 digits
    assert validate_aadhaar("34567890123").is_valid is False

    # Invalid: Starts with 0
    assert validate_aadhaar("012345678901").is_valid is False

    # Invalid: Wrong checksum
    wrong_chk = (checksum + 1) % 10
    assert validate_aadhaar(f"{prefix}{wrong_chk}").is_valid is False


def test_validate_mobile():
    # Valid standard numbers
    assert validate_mobile("9876543210").is_valid is True
    assert validate_mobile("+91 9876543210").normalized_value == "9876543210"
    assert validate_mobile("098765-43210").normalized_value == "9876543210"

    # Invalid: 9 digits
    res = validate_mobile("987654321")
    assert res.is_valid is False

    # Invalid: Starts with 5
    res = validate_mobile("5876543210")
    assert res.is_valid is False


def test_validate_date():
    spec_dob = FieldSpec(id="date_of_birth", label="Date of Birth", field_type=FieldType.DATE)

    # Valid formats
    assert validate_date("15/08/1995", spec_dob).normalized_value == "15/08/1995"
    assert validate_date("1995-08-15", spec_dob).normalized_value == "15/08/1995"
    assert validate_date("15-08-1995", spec_dob).normalized_value == "15/08/1995"

    # Future date for DOB should fail
    future_date = (date.today() + timedelta(days=365)).strftime("%d/%m/%Y")
    assert validate_date(future_date, spec_dob).is_valid is False

    # Invalid calendar date (Feb 30)
    assert validate_date("30/02/2000", spec_dob).is_valid is False


def test_validate_pin_code():
    assert validate_pin_code("400001").is_valid is True
    assert validate_pin_code("400 001").normalized_value == "400001"
    assert validate_pin_code("012345").is_valid is False
    assert validate_pin_code("40001").is_valid is False


def test_validate_choice():
    spec = FieldSpec(
        id="gender",
        label="Gender",
        field_type=FieldType.CHOICE,
        options=["Male", "Female", "Other"],
    )
    assert validate_choice("male", spec).normalized_value == "Male"
    assert validate_choice("Female", spec).normalized_value == "Female"
    assert validate_choice("Alien", spec).is_valid is False


def test_validate_name():
    assert validate_name("rajesh kumar sharma").normalized_value == "Rajesh Kumar Sharma"
    assert validate_name("A. P. J. Abdul Kalam").normalized_value == "A. P. J. Abdul Kalam"
    assert validate_name("Rajesh123").is_valid is False
