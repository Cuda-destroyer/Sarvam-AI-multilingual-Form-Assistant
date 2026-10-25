"""
Redacting Logger: Prevents sensitive personal identifiers (Aadhaar, mobile numbers, API keys)
from being written into console logs, files, or telemetry.
"""

import logging
import re
from typing import Any

# Regex patterns for sensitive data
AADHAAR_PATTERN = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")
PHONE_PATTERN = re.compile(r"\b(?:(?:\+91|0)?[6-9]\d{9})\b")
API_KEY_PATTERN = re.compile(r"(?:api[-_]subscription[-_]key|sarvam[-_]api[-_]key|Bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{8,})['\"]?", re.IGNORECASE)


def redact_text(text: str) -> str:
    """Redact sensitive patterns from text."""
    if not isinstance(text, str):
        return text

    # Redact API keys
    text = API_KEY_PATTERN.sub(r"api_key: [REDACTED]", text)

    # Redact Aadhaar numbers (mask first 8 digits, retain last 4)
    def mask_aadhaar(match: re.Match) -> str:
        raw = re.sub(r"[ -]", "", match.group(0))
        if len(raw) == 12:
            return f"XXXX-XXXX-{raw[-4:]}"
        return "[AADHAAR-REDACTED]"

    text = AADHAAR_PATTERN.sub(mask_aadhaar, text)

    # Redact phone numbers (mask middle digits)
    def mask_phone(match: re.Match) -> str:
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 10:
            last4 = digits[-4:]
            first2 = digits[-10:-8]
            return f"{first2}XXXX{last4}"
        return "[PHONE-REDACTED]"

    text = PHONE_PATTERN.sub(mask_phone, text)

    return text


class RedactingFormatter(logging.Formatter):
    """Custom logging formatter that strips PII and credentials."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_text(original)


def get_logger(name: str = "sarvam_app") -> logging.Logger:
    """Obtain a logger configured with redacting formatter."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger
