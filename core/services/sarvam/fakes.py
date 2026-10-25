"""
Mock / Fake implementations of Sarvam AI services for offline testing and CI.
Allows complete end-to-end testing without consuming live API credits or requiring network access.
"""

from typing import Any, Dict, List, Optional
from core.models import FieldSpec, FieldType


class FakeSarvamClient:
    """Mock client returning controlled responses for testing."""

    def __init__(self, should_fail: bool = False, fail_code: int = 429):
        self.should_fail = should_fail
        self.fail_code = fail_code
        self.call_history: List[Dict[str, Any]] = []

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.call_history.append({
            "endpoint": endpoint,
            "json_data": json_data,
            "data": data,
        })

        if self.should_fail:
            raise Exception(f"Simulated Sarvam Error HTTP {self.fail_code}")

        if endpoint == "speech-to-text":
            return {
                "transcript": "Rajesh Kumar",
                "language_code": data.get("language_code", "hi-IN") if data else "hi-IN",
            }
        elif endpoint == "v1/chat/completions":
            return {
                "choices": [{
                    "message": {
                        "content": '{"candidate_value": "Rajesh Kumar", "clarification_needed": false, "reason": ""}'
                    }
                }]
            }
        elif endpoint == "text-to-speech":
            return {
                "audios": ["UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="]  # Minimal valid WAV base64
            }
        elif endpoint == "transliterate":
            inp = json_data.get("input", "") if json_data else ""
            return {"transliterated_text": inp}
        elif endpoint == "translate":
            inp = json_data.get("input", "") if json_data else ""
            return {"translated_text": inp}

        return {}
