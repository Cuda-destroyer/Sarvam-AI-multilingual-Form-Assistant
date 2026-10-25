# Multilingual Form & Document Filler: Implementation Status & Living Checklist

**Last Updated:** 2026-10-25
**Project:** Sarvam AI-Powered Multilingual Form and Document Filling Assistant
**Stack:** Python 3.12, Streamlit, Sarvam AI REST API (Saaras v3 STT, Bulbul v3 TTS, Mayura / Translate, sarvam-30b/105b Chat), PyPDF, Python-docx, ReportLab, PDFPlumber, Pydantic v2.

---

## 1. Phase Status Overview

| Phase | Description | Status | Tests | Notes |
|---|---|---|---|---|
| **Phase 0** | Requirements, Form Corpus & Feasibility | **Complete** | Manual / Spec | Synthetic & sample forms generated for MVP (DOCX, AcroForm, Flat PDF) |
| **Phase 1** | Sarvam API Feasibility & Verification | **Complete** | Smoke / Fakes | Adapter contracts defined, mock/fake layer established, smoke script verified |
| **Phase 2** | Architecture & Workflow Design | **Complete** | Unit | Pydantic data models, state machine spec, privacy data flow, ADRs created |
| **Phase 3** | MVP Definition & Acceptance Criteria | **Complete** | Scenarios | 10 acceptance scenarios & demo workflow established in `docs/mvp_scope.md` |
| **Phase 4** | Repository & Environment Setup | **Complete** | Config Check | Repo structure, `.gitignore`, `pyproject.toml`, redacting logger, central config |
| **Phase 5** | Document Ingestion & Form Understanding | **Complete** | 6 Unit Tests | File gate, AcroForm extractor, flat PDF coordinate detector, DOCX walker, schema builder |
| **Phase 6** | Sarvam Service Layer & Audio Pipeline | **Complete** | Mock / Live | Centralized API client, STT adapter, LLM structured adapter, TTS adapter, transliteration, audio duration checks |
| **Phase 7** | Conversational Interview & Deterministic Validators | **Complete** | 10 Unit Tests | Aadhaar (Verhoeff checksum + masking), Mobile, DOB, Names, Choices, State machine |
| **Phase 8** | Document Generation & Round-Trip Verifier | **Complete** | 3 Round-trip Tests | DOCX writer, AcroForm writer, Flat PDF overlay writer, round-trip verification |
| **Phase 9** | Streamlit Multilingual UI | **Complete** | Browser E2E | 8 screens, accessibility pass, language switch, audio input, progress tracking verified in browser |
| **Phase 10** | Testing & Evaluation Matrix | **Complete** | 25 Tests Passing | Full test suite across edge cases, secret scanning, PII grep |
| **Phase 11** | Deployment Readiness & Health Checks | **Complete** | Health Check | Streamlit configuration, health page, session isolation, temporary file purging |
| **Phase 12** | Pilot & Improvement | **Deferred** | - | Post-MVP user testing |

---

## 2. Detailed Task Backlog

### Phase 0: Requirements & Form Corpus
- [x] Analyze PRD and Roadmap documents
- [x] Create directory structure for sample/test forms (`tests/fixtures/forms/`)
- [x] Generate representative MVP forms:
  - [x] DOCX form with tables & underscores (`college_admission_form.docx`)
  - [x] Fillable AcroForm PDF (`scholarship_application_form.pdf`)
  - [x] Flat-text PDF form (`bank_account_opening.pdf`)
- [x] Document corpus classification and two MVP input paths (DOCX + PDF)

### Phase 1: Sarvam AI Verification & Client Setup
- [x] Define official Sarvam API endpoints and contracts (`/speech-to-text`, `/v1/chat/completions`, `/text-to-speech`, `/translate`, `/transliterate`)
- [x] Create `scripts/smoke_test.py` with zero key leakage
- [x] Implement robust mock & fake adapters for CI / offline execution
- [x] Define fallbacks for rate limits, 429/503 retry with exponential backoff & jitter

### Phase 2: Architecture & Data Contracts
- [x] Pydantic models: `FormSchema`, `FieldSpec`, `FieldValue`, `Provenance`, `ValidationResult`, `SessionStateModel`
- [x] Field state machine transition table:
  - `pending` -> `asked` -> `awaiting_confirmation` -> `confirmed`
  - Recoverable loops: `ambiguous`, `invalid`, `clarification`
  - Skip & conditional branches: `optional_skipped`, `not_applicable`, `exception_recorded`
- [x] Error taxonomy: `UserFixableError`, `RetryableApiError`, `FatalSystemError`
- [x] Architectural Decision Records (ADRs) for PDF & DOCX libraries and security

### Phase 4: Environment, Security & Config
- [x] `.gitignore` guarding `.env`, `.streamlit/secrets.toml`, uploads, outputs, and caches
- [x] `core/config.py`: validated settings using `pydantic-settings` reading env vars and Streamlit secrets
- [x] Redacting logger (`core/privacy/logger.py`): masks 12-digit Aadhaar, phones, keys from all logs

### Phase 5: Ingestion & Form Understanding
- [x] File gate (`core/ingestion/file_gate.py`): magic-byte verification, size limits, page limits, path traversal defense
- [x] Ingestion extractors:
  - [x] DOCX reader: paragraphs, tables, blanks, underscores (`core/ingestion/docx_reader.py`)
  - [x] AcroForm PDF reader: field name, type, rect, options (`core/ingestion/pdf_acroform.py`)
  - [x] Flat-text PDF extractor: coordinate words, blanks, underscores (`core/ingestion/pdf_text.py`)
- [x] Schema builder (`core/ingestion/schema_builder.py`): deterministic field detection + LLM enrichment

### Phase 6: Sarvam Service Layer
- [x] Base adapter & HTTP client with bounded retries and timeout (`core/services/sarvam/client.py`)
- [x] STT Service (Saaras v3, max 30s audio cap, mono wav check) (`core/services/sarvam/stt.py`)
- [x] LLM Structured Extractor (JSON schema constrained) (`core/services/sarvam/llm.py`)
- [x] TTS & Translation/Transliteration services (`core/services/sarvam/speech_lang.py`)
- [x] Test fakes for deterministic CI testing (`core/services/sarvam/fakes.py`)

### Phase 7: Interview Controller & Deterministic Validators
- [x] Verhoeff checksum algorithm for Aadhaar validation
- [x] Validators:
  - [x] Aadhaar: length, Verhoeff checksum, masking
  - [x] Mobile: 10-digit Indian mobile validation (6-9 starting), prefix normalization
  - [x] Date of Birth / Dates: calendar correctness, past/future bounds, format normalization
  - [x] Names: transliteration handling, character restrictions, no semantic translation
  - [x] Address components & PIN (6 digits)
  - [x] Multiple choice & enumerations mapping
  - [x] Conditionals & skip rules
- [x] Interview state machine & question controller (`core/interview/controller.py`)

### Phase 8: Document Generation & Round-Trip Verifier
- [x] DOCX Generator (`core/generation/docx_writer.py`)
- [x] AcroForm PDF Generator (`core/generation/pdf_acroform_writer.py`)
- [x] Flat PDF Overlay Generator (`core/generation/pdf_overlay_writer.py`)
- [x] Round-Trip Verifier (`core/generation/verifier.py`): re-extract text, prove 100% presence of confirmed values

### Phase 9: Streamlit User Experience
- [x] Screen 1: Welcome & Consent (Clear data minimization notice)
- [x] Screen 2: Document Upload & File Gate Validation
- [x] Screen 3: Form Analysis Summary & Confirmation
- [x] Screen 4: Language Selection (Hindi, Marathi, Tamil, English, Bengali, etc.)
- [x] Screen 5: Guided Conversational Interview (one question at a time, audio + text fallback, progress bar)
- [x] Screen 6: Final Review, Provenance Inspection & In-place Correction
- [x] Screen 7: Generation, Verification Report & Download
- [x] Screen 8: Session Wipe & Cleanup

### Phase 10: Verification, Testing & QA
- [x] Unit test suite for validators (Aadhaar Verhoeff, Mobile, Date, Name, Choice)
- [x] Unit test suite for Ingestion (DOCX, AcroForm, Flat PDF, File Gate)
- [x] Unit test suite for Document Generation and Round-trip Verification
- [x] Interview Controller state machine test suite
- [x] Secret scanning and logging redaction test suite
- [x] Live/Mock Sarvam adapter contract tests
