# Sarvam AI API Verification & Architecture Notes

**Verification Date:** 2026-10-25  
**Provider:** Sarvam AI (`https://api.sarvam.ai`)

---

## 1. Verified Endpoint Specifications

| Capability | Official Endpoint / Model | Auth Header | Constraints & Notes |
|---|---|---|---|
| **Speech-to-Text (STT)** | `POST /speech-to-text`<br>Model: `saaras:v3` | `api-subscription-key: <KEY>` | Max 30 seconds for REST endpoint. Supported modes: `transcribe`, `translate`, `verbatim`, `translit`, `codemix`. Language detection via `language_code="unknown"` or ISO code (e.g., `hi-IN`). |
| **Text-to-Speech (TTS)** | `POST /text-to-speech`<br>Model: `bulbul:v3` | `api-subscription-key: <KEY>` | Returns base64 audio (WAV). Requires `target_language_code` and `inputs` string list. |
| **Translation** | `POST /translate`<br>Model: `mayura:v1` | `api-subscription-key: <KEY>` | Translates text between Indian languages and English. |
| **Transliteration** | `POST /transliterate` | `api-subscription-key: <KEY>` | Converts Indian script text to Latin script (essential for proper names). |
| **Chat / LLM Extraction** | `POST /v1/chat/completions`<br>Models: `sarvam-30b`, `sarvam-105b` | `api-subscription-key: <KEY>` | Supports `response_format={"type": "json_schema", ...}` for schema-constrained deterministic candidate extraction. |

## 2. Authentication & Error Taxonomy
- Header: `api-subscription-key: <KEY>`
- Auth failure: Returns HTTP 403 (Forbidden) instead of 401 on Sarvam gateways.
- Rate limits: Returns HTTP 429 when throttled. Handled with exponential backoff + jitter.
- Server overload: Returns HTTP 503. Handled with bounded retry (max 3 retries) and graceful fallback to text input.
