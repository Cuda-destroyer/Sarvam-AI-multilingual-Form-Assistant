"""
LLM Service using Sarvam AI Chat Models (sarvam-30b / sarvam-105b).
Used for schema-constrained candidate value extraction and conversational explanation.
Deterministic validators always have final authority over LLM outputs.
"""

import json
from typing import Any, Dict, List, Optional
from core.config import get_config
from core.models import FieldSpec, FieldType
from core.privacy.logger import get_logger
from core.services.sarvam.client import SarvamClient

logger = get_logger("sarvam_llm")


class LLMService:
    """Service wrapper for Sarvam AI Chat Completions."""

    def __init__(self, client: Optional[SarvamClient] = None):
        self.client = client or SarvamClient()
        self.config = get_config()

    def interpret_answer(
        self,
        raw_text: str,
        spec: FieldSpec,
        language_code: str = "hi-IN",
    ) -> Dict[str, Any]:
        """
        Extract structured candidate answer from natural language speech transcript or text.
        Returns a dict e.g. {"candidate_value": "...", "confidence": 0.9, "clarification_needed": false}
        """
        system_prompt = (
            "You are an accurate, objective form-filling assistant. "
            "Your task is to extract the specific value requested by the form field from the user's natural language answer.\n"
            "Rules:\n"
            "1. Output ONLY a valid JSON object.\n"
            "2. Never fabricate or guess missing information.\n"
            "3. If the user's answer is ambiguous or incomplete, set 'clarification_needed': true and explain why.\n"
            "4. Do not translate proper names; keep their phonetic spelling or transliteration.\n"
            "5. Convert natural language dates to DD/MM/YYYY if unambiguous."
        )

        user_content = (
            f"<field_definition>\n"
            f"Field ID: {spec.id}\n"
            f"Label: {spec.label}\n"
            f"Type: {spec.field_type.value}\n"
            f"Allowed Options: {spec.options if spec.options else 'Any'}\n"
            f"</field_definition>\n\n"
            f"<untrusted_user_input language='{language_code}'>\n"
            f"{raw_text}\n"
            f"</untrusted_user_input>\n\n"
            f"Extract the exact value for this field in JSON format:\n"
            f'{{"candidate_value": "<extracted value or null>", "clarification_needed": false, "reason": ""}}'
        )

        payload = {
            "model": self.config.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 256,
        }

        try:
            response = self.client.post("v1/chat/completions", json_data=payload)
            content_str = response["choices"][0]["message"]["content"]
            parsed = json.loads(content_str)
            return {
                "candidate_value": str(parsed.get("candidate_value", "")).strip(),
                "clarification_needed": bool(parsed.get("clarification_needed", False)),
                "reason": parsed.get("reason", ""),
            }
        except Exception as e:
            logger.warning("LLM extraction failed or returned malformed JSON (%s). Falling back to raw text.", str(e))
            # Safe deterministic fallback: return trimmed raw text
            return {
                "candidate_value": raw_text.strip(),
                "clarification_needed": False,
                "reason": "fallback_to_raw",
            }

    def generate_question_prompt(
        self,
        spec: FieldSpec,
        language_code: str,
    ) -> str:
        """
        Formulate a clear, friendly question asking for the field value in the user's chosen language.
        Uses cached/predefined explanations where available.
        """
        # Return pre-defined explanation if available
        if language_code in spec.explanation and spec.explanation[language_code]:
            return spec.explanation[language_code]

        # Standard deterministic prompts for common fields
        prompts = {
            "hi-IN": {
                FieldType.NAME: f"कृपया अपना {spec.label} बताएं।",
                FieldType.AADHAAR: "कृपया अपना 12 अंकों का आधार नंबर बताएं।",
                FieldType.MOBILE: "कृपया अपना 10 अंकों का मोबाइल नंबर बताएं।",
                FieldType.DATE: f"कृपया {spec.label} की तारीख (दिन, माह, वर्ष) बताएं।",
                FieldType.CHOICE: f"कृपया इनमें से अपना विकल्प चुनें: {', '.join(spec.options)}",
                FieldType.EMAIL: "कृपया अपना ईमेल पता बताएं।",
                FieldType.ADDRESS: f"कृपया अपना {spec.label} विस्तार से बताएं।",
            },
            "mr-IN": {
                FieldType.NAME: f"कृपया आपले {spec.label} सांगा.",
                FieldType.AADHAAR: "कृपया आपला 12 अंकी आधार क्रमांक सांगा.",
                FieldType.MOBILE: "कृपया आपला 10 अंकी मोबाईल क्रमांक सांगा.",
                FieldType.DATE: f"कृपया {spec.label} तारीख (दिवस, महिना, वर्ष) सांगा.",
                FieldType.CHOICE: f"कृपया यापैकी एक पर्याय निवडा: {', '.join(spec.options)}",
                FieldType.EMAIL: "कृपया आपला ईमेल पत्ता सांगा.",
                FieldType.ADDRESS: f"कृपया आपला {spec.label} सविस्तर सांगा.",
            },
            "ta-IN": {
                FieldType.NAME: f"தயவுசெய்து உங்கள் {spec.label} கூறவும்.",
                FieldType.AADHAAR: "தயவுசெய்து உங்கள் 12 இலக்க ஆதார் எண்ணைக் கூறவும்.",
                FieldType.MOBILE: "தயவுசெய்து உங்கள் 10 இலக்க மொபைல் எண்ணைக் கூறவும்.",
                FieldType.DATE: f"தயவுசெய்து {spec.label} தேதியைத் தெரிவிக்கவும்.",
                FieldType.CHOICE: f"தயவுசெய்து இவற்றில் ஒன்றைத் தேர்ந்தெடுக்கவும்: {', '.join(spec.options)}",
                FieldType.EMAIL: "தயவுசெய்து உங்கள் மின்னஞ்சல் முகவரியைக் கூறவும்.",
                FieldType.ADDRESS: f"தயவுசெய்து உங்கள் {spec.label} முகவரியைக் கூறவும்.",
            },
            "en-IN": {
                FieldType.NAME: f"Please provide your {spec.label}.",
                FieldType.AADHAAR: "Please provide your 12-digit Aadhaar number.",
                FieldType.MOBILE: "Please provide your 10-digit mobile number.",
                FieldType.DATE: f"Please provide your {spec.label} (DD/MM/YYYY).",
                FieldType.CHOICE: f"Please choose one of the following options: {', '.join(spec.options)}",
                FieldType.EMAIL: "Please provide your email address.",
                FieldType.ADDRESS: f"Please provide your {spec.label}.",
            },
        }

        lang_prompts = prompts.get(language_code, prompts["en-IN"])
        if spec.field_type in lang_prompts:
            return lang_prompts[spec.field_type]

        # Generic default
        return f"Please provide your {spec.label}."
