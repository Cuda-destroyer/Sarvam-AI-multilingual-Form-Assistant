"""
Unit tests for Redacting Logger ensuring sensitive PII is masked.
"""

from core.privacy.logger import redact_text


def test_redact_aadhaar():
    text = "User entered Aadhaar 2345 6789 0123 for KYC."
    redacted = redact_text(text)
    assert "2345" not in redacted
    assert "XXXX-XXXX-0123" in redacted


def test_redact_mobile():
    text = "Call user at 9876543210 immediately."
    redacted = redact_text(text)
    assert "9876543210" not in redacted
    assert "98XXXX3210" in redacted


def test_redact_api_key():
    text = "Request failed with api-subscription-key: secret_sarvam_key_abc123"
    redacted = redact_text(text)
    assert "secret_sarvam_key_abc123" not in redacted
    assert "[REDACTED]" in redacted
