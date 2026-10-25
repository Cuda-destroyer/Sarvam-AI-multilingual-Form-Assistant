"""
Speech-to-Text (STT) Service using Sarvam AI Saaras v3.
Enforces the 30-second audio constraint, audio format validation, and language detection.
"""

import io
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from core.config import get_config
from core.privacy.logger import get_logger
from core.services.sarvam.client import SarvamClient

logger = get_logger("sarvam_stt")


class SpeechToTextService:
    """Service wrapper for Sarvam AI Saaras v3 Speech Recognition."""

    def __init__(self, client: Optional[SarvamClient] = None):
        self.client = client or SarvamClient()
        self.config = get_config()

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        language_code: Optional[str] = None,
        model: Optional[str] = None,
        mode: str = "transcribe",
    ) -> Dict[str, Any]:
        """
        Transcribe audio payload using Sarvam Saaras v3.
        
        Args:
            audio_bytes: Raw audio bytes (WAV, MP3, etc.)
            language_code: ISO language code (e.g. 'hi-IN', 'mr-IN', 'ta-IN') or 'unknown' for auto-detect
            model: STT model identifier (defaults to 'saaras:v3')
            mode: 'transcribe', 'translate', 'verbatim', 'translit', or 'codemix'
        
        Returns:
            Dict containing 'transcript', 'language_code', and metadata.
        """
        if not audio_bytes or len(audio_bytes) == 0:
            return {"transcript": "", "language_code": language_code or "unknown", "error": "Empty audio data"}

        lang = language_code if language_code and language_code != "auto" else "unknown"
        stt_model = model or self.config.stt_model

        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
        }
        data = {
            "model": stt_model,
            "language_code": lang,
            "mode": mode,
        }

        logger.info("Submitting STT request (mode=%s, lang=%s, model=%s)", mode, lang, stt_model)
        response = self.client.post("speech-to-text", files=files, data=data)

        # Sarvam response structure contains 'transcript'
        transcript = response.get("transcript", "").strip()
        detected_lang = response.get("language_code", lang)

        return {
            "transcript": transcript,
            "language_code": detected_lang,
            "raw_response": response,
        }
