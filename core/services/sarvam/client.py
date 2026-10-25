"""
Sarvam AI Centralized HTTP Client.
Handles authentication, request dispatch, bounded retries with exponential backoff,
circuit breaking, and privacy-conscious error management.
"""

import time
from typing import Any, Dict, Optional
import httpx
from core.config import get_config
from core.privacy.logger import get_logger

logger = get_logger("sarvam_client")


class SarvamApiError(Exception):
    """Base class for Sarvam API exceptions."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SarvamAuthError(SarvamApiError):
    """Authentication or authorization error (e.g. HTTP 403)."""
    pass


class SarvamRateLimitError(SarvamApiError):
    """Rate limit exceeded (HTTP 429)."""
    pass


class SarvamServerError(SarvamApiError):
    """Temporary server failure or overload (HTTP 500, 502, 503, 504)."""
    pass


class SarvamClient:
    """HTTP client adapter for Sarvam AI REST API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 30.0):
        config = get_config()
        self.api_key = api_key or config.sarvam_api_key or ""
        self.base_url = (base_url or config.sarvam_base_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = 3

    def _get_headers(self) -> Dict[str, str]:
        """Headers required by Sarvam API."""
        return {
            "api-subscription-key": self.api_key,
            "User-Agent": "SarvamMultilingualFormFiller/1.0",
        }

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute POST request with exponential backoff for 429/503.
        """
        if not self.api_key:
            raise SarvamAuthError("Sarvam API key is not configured. Please set SARVAM_API_KEY in .env or secrets.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        # For multipart uploads, httpx sets boundary automatically; do not force application/json
        if json_data is not None and not files:
            headers["Content-Type"] = "application/json"

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        url=url,
                        headers=headers,
                        json=json_data,
                        files=files,
                        data=data,
                        params=params,
                    )

                if response.status_code in (200, 201):
                    return response.json()

                if response.status_code == 403:
                    raise SarvamAuthError(
                        "Authentication failed with Sarvam AI (HTTP 403). Check your SARVAM_API_KEY.",
                        status_code=403,
                        response_body=response.text,
                    )

                if response.status_code == 429:
                    logger.warning("Sarvam API rate limit encountered (attempt %d/%d). Backing off...", attempt, self.max_retries)
                    if attempt < self.max_retries:
                        time.sleep(1.5 * attempt)
                        continue
                    raise SarvamRateLimitError(
                        "Sarvam API rate limit exceeded. Please wait a moment before trying again.",
                        status_code=429,
                        response_body=response.text,
                    )

                if response.status_code in (500, 502, 503, 504):
                    logger.warning("Sarvam server error HTTP %d (attempt %d/%d).", response.status_code, attempt, self.max_retries)
                    if attempt < self.max_retries:
                        time.sleep(1.0 * attempt)
                        continue
                    raise SarvamServerError(
                        f"Sarvam AI service temporarily unavailable (HTTP {response.status_code}).",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # Other 4xx client errors
                raise SarvamApiError(
                    f"Sarvam API request error: HTTP {response.status_code} - {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning("Network issue calling Sarvam %s: %s (attempt %d/%d)", endpoint, str(e), attempt, self.max_retries)
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)
                    continue

        raise SarvamApiError(f"Request failed after {self.max_retries} attempts: {str(last_exception)}")
