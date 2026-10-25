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
        language_code: str = "hi-IN",
    ) -> str:
        """
        Formulate a clear, natural question in the user's chosen language.
        Translates dynamically via Sarvam Translate if needed, and caches the result.
        """
        # If English requested, return clean English prompt
        if language_code == "en-IN":
            return f"Please provide your {spec.label}."

        # Check if already translated to native script
        cached = spec.explanation.get(language_code)
        if cached:
            # Verify cached explanation is actually in native Indic script (not English fallback)
            has_indic = any("\u0900" <= ch <= "\u0D7F" for ch in cached)
            if has_indic:
                return cached

        # Check semantic field ID & label for natural native phrasing
        label_lower = spec.label.lower()
        fid_lower = spec.id.lower()

        # Comprehensive native prompt catalog for all supported Indian languages
        native_catalog = {
            "hi-IN": {
                "name": "कृपया अपना पूरा नाम बताएं।",
                "father": "कृपया अपने पिता का नाम बताएं।",
                "mother": "कृपया अपनी माता का नाम बताएं।",
                "dob": "कृपया अपनी जन्म तिथि (दिन/माह/वर्ष) बताएं।",
                "aadhaar": "कृपया अपना 12 अंकों का आधार नंबर बताएं।",
                "mobile": "कृपया अपना 10 अंकों का मोबाइल नंबर बताएं।",
                "email": "कृपया अपना ईमेल पता बताएं।",
                "address": "कृपया अपना पूरा आवासीय पता बताएं।",
                "pin": "कृपया अपना 6 अंकों का पिन कोड बताएं।",
                "gender": "कृपया अपना लिंग (पुरुष / महिला / अन्य) चुनें।",
            },
            "mr-IN": {
                "name": "कृपया आपले पूर्ण नाव सांगा.",
                "father": "कृपया आपल्या वडिलांचे नाव सांगा.",
                "mother": "कृपया आपल्या आईचे नाव सांगा.",
                "dob": "कृपया आपली जन्मतारीख (दिवस/महिना/वर्ष) सांगा.",
                "aadhaar": "कृपया आपला 12 अंकी आधार क्रमांक सांगा.",
                "mobile": "कृपया आपला 10 अंकी मोबाईल क्रमांक सांगा.",
                "email": "कृपया आपला ईमेल पत्ता सांगा.",
                "address": "कृपया आपला संपूर्ण पत्ता सांगा.",
                "pin": "कृपया आपला 6 अंकी पिन कोड सांगा.",
                "gender": "कृपया आपले लिंग निवडा.",
            },
            "ta-IN": {
                "name": "தயவுசெய்து உங்கள் முழுப் பெயரைத் தெரிவிக்கவும்.",
                "father": "தயவுசெய்து உங்கள் தந்தையின் பெயரைத் தெரிவிக்கவும்.",
                "mother": "தயவுசெய்து உங்கள் தாயின் பெயரைத் தெரிவிக்கவும்.",
                "dob": "தயவுசெய்து உங்கள் பிறந்த தேதியைத் (நாள்/மாதம்/ஆண்டு) தெரிவிக்கவும்.",
                "aadhaar": "தயவுசெய்து உங்கள் 12 இலக்க ஆதார் எண்ணைத் தெரிவிக்கவும்.",
                "mobile": "தயவுசெய்து உங்கள் 10 இலக்க மொபைல் எண்ணைத் தெரிவிக்கவும்.",
                "email": "தயவுசெய்து உங்கள் மின்னஞ்சல் முகவரியைத் தெரிவிக்கவும்.",
                "address": "தயவுசெய்து உங்கள் முழு முகவரியைத் தெரிவிக்கவும்.",
                "pin": "தயவுசெய்து உங்கள் 6 இலக்க பின்கோடைத் தெரிவிக்கவும்.",
                "gender": "தயவுசெய்து உங்கள் பாலினத்தைத் தேர்ந்தெடுக்கவும்.",
            },
            "te-IN": {
                "name": "దయచేసి మీ పూర్తి పేరును తెలియజేయండి.",
                "father": "దయచేసి మీ తండ్రిగారి పేరును తెలియజేయండి.",
                "mother": "దయచేసి మీ తల్లిగారి పేరును తెలియజేయండి.",
                "dob": "దయచేసి మీ పుట్టిన తేదీని (రోజు/నెల/సంవత్సరం) తెలియజేయండి.",
                "aadhaar": "దయచేసి మీ 12 అంకెల ఆధార్ నంబర్‌ను తెలియజేయండి.",
                "mobile": "దయచేసి మీ 10 అంకెల మొబైల్ నంబర్‌ను తెలియజేయండి.",
                "email": "దయచేసి మీ ఇమెయిల్ చిరునామాను తెలియజేయండి.",
                "address": "దయచేసి మీ పూర్తి చిరునామాను తెలియజేయండి.",
                "pin": "దయచేసి మీ 6 అంకెల పిన్ కోడ్‌ను తెలియజేయండి.",
                "gender": "దయచేసి మీ లింగాన్ని ఎంచుకోండి.",
            },
            "bn-IN": {
                "name": "অনুগ্রহ করে আপনার পুরো নাম বলুন।",
                "father": "অনুগ্রহ করে আপনার বাবার নাম বলুন।",
                "mother": "অনুগ্রহ করে আপনার মায়ের নাম বলুন।",
                "dob": "অনুগ্রহ করে আপনার জন্ম তারিখ (দিন/মাস/বছর) প্রদান করুন।",
                "aadhaar": "অনুগ্রহ করে আপনার ১২ সংখ্যার আধার নম্বরটি লিখুন।",
                "mobile": "অনুগ্রহ করে আপনার ১০ সংখ্যার মোবাইল নম্বরটি লিখুন।",
                "email": "অনুগ্রহ করে আপনার ইমেল ঠিকানা প্রদান করুন।",
                "address": "অনুগ্রহ করে আপনার সম্পূর্ণ ঠিকানা প্রদান করুন।",
                "pin": "অনুগ্রহ করে আপনার ৬ সংখ্যার পিন কোড প্রদান করুন।",
                "gender": "অনুগ্রহ করে আপনার লিঙ্গ নির্বাচন করুন।",
            },
            "gu-IN": {
                "name": "કૃપા કરીને તમારું પૂરું નામ જણાવો.",
                "father": "કૃપા કરીને તમારા પિતાનું નામ જણાવો.",
                "mother": "કૃપા કરીને તમારી માતાનું નામ જણાવો.",
                "dob": "કૃપા કરીને તમારી જન્મ તારીખ (દિવસ/મહિનો/વર્ષ) જણાવો.",
                "aadhaar": "કૃપા કરીને તમારો 12 અંકનો આધાર નંબર જણાવો.",
                "mobile": "કૃપા કરીને તમારો 10 અંકનો મોબાઇલ નંબર જણાવો.",
                "email": "કૃપા કરીને તમારું ઇમેઇલ સરનામું જણાવો.",
                "address": "કૃપા કરીને તમારું પૂરું સરનામું જણાવો.",
                "pin": "કૃપા કરીને તમારો 6 અંકનો પિન કોડ જણાવો.",
                "gender": "કૃપા કરીને તમારું લિંગ પસંદ કરો.",
            },
            "kn-IN": {
                "name": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರನ್ನು ತಿಳಿಸಿ.",
                "father": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ತಂದೆಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ.",
                "mother": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ತಾಯಿಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ.",
                "dob": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಜನ್ಮ ದಿನಾಂಕವನ್ನು (ದಿನ/ತಿಂಗಳು/ವರ್ಷ) ತಿಳಿಸಿ.",
                "aadhaar": "ದಯವಿಟ್ಟು ನಿಮ್ಮ 12 ಅಂಕಿಗಳ ಆಧಾರ್ ಸಂಖ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
                "mobile": "ದಯವಿಟ್ಟು ನಿಮ್ಮ 10 ಅಂಕಿಗಳ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
                "email": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಇಮೇಲ್ ವಿಳಾಸವನ್ನು ತಿಳಿಸಿ.",
                "address": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪೂರ್ಣ ವಿಳಾಸವನ್ನು ತಿಳಿಸಿ.",
                "pin": "ದಯವಿಟ್ಟು ನಿಮ್ಮ 6 ಅಂಕಿಗಳ ಪಿನ್ ಕೋಡ್ ತಿಳಿಸಿ.",
                "gender": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಲಿಂಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
            },
            "pa-IN": {
                "name": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਪੂਰਾ ਨਾਮ ਦੱਸੋ।",
                "father": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਪਿਤਾ ਜੀ ਦਾ ਨਾਮ ਦੱਸੋ।",
                "mother": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਮਾਤਾ ਜੀ ਦਾ ਨਾਮ ਦੱਸੋ।",
                "dob": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਜਨਮ ਮਿਤੀ (ਦਿਨ/ਮਹੀਨਾ/ਸਾਲ) ਦੱਸੋ।",
                "aadhaar": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 12 ਅੰਕਾਂ ਦਾ ਆਧਾਰ ਨੰਬਰ ਦੱਸੋ।",
                "mobile": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 10 ਅੰਕਾਂ ਦਾ ਮੋਬਾਈਲ ਨੰਬਰ ਦੱਸੋ।",
                "email": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਈਮੇਲ ਪਤਾ ਦੱਸੋ।",
                "address": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਪੂਰਾ ਪਤਾ ਦੱਸੋ।",
                "pin": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 6 ਅੰਕਾਂ ਦਾ ਪਿੰਨ ਕੋਡ ਦੱਸੋ।",
                "gender": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਲਿੰਗ ਚੁਣੋ।",
            },
        }

        lang_dict = native_catalog.get(language_code)
        if lang_dict:
            if "aadhaar" in fid_lower or "aadhaar" in label_lower or "uid" in fid_lower:
                spec.explanation[language_code] = lang_dict["aadhaar"]
                return lang_dict["aadhaar"]
            if "mobile" in fid_lower or "phone" in fid_lower or "contact" in fid_lower:
                spec.explanation[language_code] = lang_dict["mobile"]
                return lang_dict["mobile"]
            if "birth" in fid_lower or "dob" in fid_lower:
                spec.explanation[language_code] = lang_dict["dob"]
                return lang_dict["dob"]
            if "father" in fid_lower or "father" in label_lower:
                spec.explanation[language_code] = lang_dict["father"]
                return lang_dict["father"]
            if "mother" in fid_lower or "mother" in label_lower:
                spec.explanation[language_code] = lang_dict["mother"]
                return lang_dict["mother"]
            if "name" in fid_lower or "name" in label_lower or spec.field_type == FieldType.NAME:
                spec.explanation[language_code] = lang_dict["name"]
                return lang_dict["name"]
            if "email" in fid_lower or "mail" in label_lower:
                spec.explanation[language_code] = lang_dict["email"]
                return lang_dict["email"]
            if "pin" in fid_lower or "postal" in label_lower:
                spec.explanation[language_code] = lang_dict["pin"]
                return lang_dict["pin"]
            if "gender" in fid_lower or "sex" in label_lower:
                spec.explanation[language_code] = lang_dict["gender"]
                return lang_dict["gender"]
            if "address" in fid_lower or "address" in label_lower or spec.field_type == FieldType.ADDRESS:
                spec.explanation[language_code] = lang_dict["address"]
                return lang_dict["address"]

        # Dynamic Translation via Sarvam Translate (Mayura v1) for any specific or custom field label
        english_prompt = f"Please provide your {spec.label}."
        if spec.options:
            english_prompt += f" Options: {', '.join(spec.options)}."

        if self.config.is_sarvam_configured():
            try:
                payload = {
                    "input": english_prompt,
                    "source_language_code": "en-IN",
                    "target_language_code": language_code,
                    "model": self.config.translate_model,
                }
                res = self.client.post("translate", json_data=payload)
                translated = res.get("translated_text", "").strip()
                if translated:
                    logger.info("Translated question for '%s' into %s: %s", spec.id, language_code, translated)
                    spec.explanation[language_code] = translated
                    return translated
            except Exception as e:
                logger.warning("Dynamic question translation failed (%s). Using fallback template.", str(e))

        # Fallback template if translation unavailable
        templates = {
            "hi-IN": f"कृपया अपना {spec.label} प्रदान करें।",
            "mr-IN": f"कृपया आपले {spec.label} प्रदान करा.",
            "ta-IN": f"தயவுசெய்து உங்கள் {spec.label} வழங்கவும்.",
            "te-IN": f"దయచేసి మీ {spec.label} అందించండి.",
            "bn-IN": f"অনুগ্রহ করে আপনার {spec.label} প্রদান করুন।",
            "gu-IN": f"કૃપા કરીને તમારું {spec.label} આપો.",
            "kn-IN": f"ದಯವಿಟ್ಟು ನಿಮ್ಮ {spec.label} ನೀಡಿ.",
            "pa-IN": f"ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ {spec.label} ਦਿਓ।",
        }
        res_prompt = templates.get(language_code, english_prompt)
        spec.explanation[language_code] = res_prompt
        return res_prompt
