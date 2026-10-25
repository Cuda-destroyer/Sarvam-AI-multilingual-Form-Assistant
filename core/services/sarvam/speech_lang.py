"""
Sarvam AI Speech & Language Services:
- TTS (Bulbul v3)
- Translation (Mayura v1)
- Transliteration (to Latin script for proper names)
"""

import base64
from typing import Any, Dict, List, Optional
from core.config import get_config
from core.privacy.logger import get_logger
from core.services.sarvam.client import SarvamClient

logger = get_logger("sarvam_speech_lang")


class SpeechLanguageService:
    """Service wrapper for Sarvam TTS, Translation, and Transliteration."""

    def __init__(self, client: Optional[SarvamClient] = None):
        self.client = client or SarvamClient()
        self.config = get_config()

    def text_to_speech(
        self,
        text: str,
        target_language_code: str = "hi-IN",
        speaker: str = "priya",
    ) -> Optional[bytes]:
        """
        Synthesize speech audio for question prompts using Bulbul v3.
        Returns raw audio bytes (WAV) or None if synthesis fails.
        """
        if not text or not text.strip():
            return None

        # Bulbul v3 supports 11 Indian languages
        supported_tts_langs = {
            "hi-IN", "bn-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN", "gu-IN", "en-IN"
        }
        lang = target_language_code if target_language_code in supported_tts_langs else "hi-IN"

        payload = {
            "inputs": [text.strip()[:500]],  # Cap prompt length
            "target_language_code": lang,
            "speaker": speaker,
            "model": self.config.tts_model,
        }

        try:
            response = self.client.post("text-to-speech", json_data=payload)
            # Sarvam returns {"audios": ["base64_encoded_audio..."]}
            audios = response.get("audios", [])
            if audios and len(audios) > 0:
                return base64.b64decode(audios[0])
        except Exception as e:
            logger.warning("TTS generation skipped or failed (%s). Continuing text-only.", str(e))

        return None

    def transliterate_to_latin(
        self,
        text: str,
        source_language_code: str = "hi-IN",
    ) -> str:
        """
        Transliterate Indian script proper names into English/Latin script.
        Never translates names semantically.
        """
        if not text or not text.strip():
            return ""

        payload = {
            "input": text.strip(),
            "source_language_code": source_language_code,
            "target_language_code": "en-IN",
        }

        try:
            response = self.client.post("transliterate", json_data=payload)
            transliterated = response.get("transliterated_text", "").strip()
            if transliterated:
                return transliterated
        except Exception as e:
            logger.warning("Transliteration failed (%s). Retaining original text.", str(e))

        return text.strip()

    def translate_to_english(
        self,
        text: str,
        source_language_code: str = "hi-IN",
    ) -> str:
        """
        Translate descriptive answers into English using Mayura v1.
        """
        if not text or not text.strip():
            return ""

        if source_language_code == "en-IN":
            return text.strip()

        payload = {
            "input": text.strip(),
            "source_language_code": source_language_code,
            "target_language_code": "en-IN",
            "model": self.config.translate_model,
        }

        try:
            response = self.client.post("translate", json_data=payload)
            translated = response.get("translated_text", "").strip()
            if translated:
                return translated
        except Exception as e:
            logger.warning("Translation failed (%s). Retaining original text.", str(e))

        return text.strip()
