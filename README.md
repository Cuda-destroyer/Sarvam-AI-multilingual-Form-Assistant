# Sarvam AI Multilingual Form & Document Filling Assistant

An intelligent, multilingual, voice-and-text enabled form completion assistant built for India.

This application allows citizens to complete English-language institutional forms (college admissions, scholarships, government benefits, bank KYC, and hospital registrations) by speaking or typing naturally in regional Indian languages (Hindi, Marathi, Tamil, Bengali, Telugu, Kannada, Gujarati, Punjabi, and English).

---

## 🌟 Core Highlights & Architectural Principles

1. **Deterministic First, LLM Second:**
   - Field format, length, and checksums (e.g. 12-digit Indian Aadhaar via the Verhoeff algorithm, 10-digit mobile, calendar dates) are validated deterministically in Python.
   - The LLM assists with natural language understanding and multilingual explanations, but never overrides deterministic rules or fabricates personal information.
2. **Nothing Enters Unconfirmed:**
   - Every answer carries full provenance: raw transcript, input method (`speech` or `text`), spoken language, normalization method, and confirmation timestamp.
   - Users review every answer via explicit read-back confirmation.
3. **Conversational Language ≠ Document Language:**
   - Spoken interview is conducted in the user's preferred native language (e.g., Hindi, Marathi, Tamil).
   - Document output is generated in official English as expected by the receiving institution.
4. **Multi-Format Document Support:**
   - **Microsoft Word (.docx):** Table cells and paragraph placeholders are populated directly while preserving styles and formatting.
   - **Interactive AcroForm PDFs:** Form fields are filled directly using `pypdf`.
   - **Flat Text PDFs:** Coordinate-based text overlays are drawn using ReportLab and merged with `pypdf`.
5. **Round-Trip Output Verification:**
   - After generating the output file, the system re-opens and re-extracts the document to verify that 100% of confirmed values are present at their designated anchors before offering the download.
6. **Privacy by Design:**
   - Automated redacting logger masks sensitive PII (Aadhaar numbers masked as `XXXX-XXXX-NNNN`, mobile numbers) and API keys.
   - Uploaded files, temporary audio recordings, and generated documents are kept in ephemeral session storage and wiped upon session completion.

---

## 🛠️ Project Structure

```text
├── app/
│   ├── main.py                     # Streamlit entry point and 8-screen router
│   ├── components/                 # UI styling, branding, and stepper components
│   └── i18n/                       # Multilingual UI strings (hi-IN, mr-IN, ta-IN, en-IN)
├── core/
│   ├── config.py                   # Pydantic Settings reading .env and Streamlit secrets
│   ├── models.py                   # Pydantic v2 data models (FormSchema, FieldSpec, FieldValue, Provenance)
│   ├── privacy/
│   │   └── logger.py               # Redacting logger stripping PII and credentials
│   ├── validation/
│   │   ├── verhoeff.py             # Verhoeff checksum algorithm for Aadhaar validation
│   │   ├── validators.py           # Deterministic validators (Aadhaar, Mobile, Dates, Names, Choices)
│   │   └── registry.py             # Semantic and type-based validator registry
│   ├── ingestion/
│   │   ├── file_gate.py            # Magic-byte check, size/page limits, filename sanitization
│   │   ├── docx_reader.py          # Word document tables and paragraph placeholder extractor
│   │   ├── pdf_acroform.py         # Interactive fillable PDF field extractor
│   │   ├── pdf_text.py             # Flat PDF text and coordinate blank detector
│   │   └── schema_builder.py       # Unified FormSchema assembly and multilingual enrichment
│   ├── generation/
│   │   ├── docx_writer.py          # DOCX template populator
│   │   ├── pdf_acroform_writer.py  # AcroForm PDF form field writer
│   │   ├── pdf_overlay_writer.py   # Coordinate overlay merger for flat PDFs
│   │   └── verifier.py             # Round-trip output verifier
│   ├── interview/
│   │   └── controller.py           # Conversational state machine and navigation controller
│   └── services/sarvam/
│       ├── client.py               # Base HTTP client with backoff and retry for 429/503
│       ├── stt.py                  # Saaras v3 Speech-to-Text adapter (<= 30s cap)
│       ├── llm.py                  # sarvam-30b / sarvam-105b schema-constrained chat adapter
│       ├── speech_lang.py          # Bulbul v3 TTS, Mayura v1 Translation, and Transliteration
│       └── fakes.py                # Deterministic offline mock adapters for CI and local testing
├── config/                         # Validation rules and language configuration
├── docs/                           # Implementation status, MVP scope, privacy notice, verification
├── scripts/
│   ├── smoke_test.py               # Safe API connectivity check (zero key leakage)
│   └── generate_fixtures.py        # Generates deterministic DOCX and PDF test forms
├── tests/
│   ├── fixtures/forms/             # Sample blank institutional forms
│   ├── test_e2e_workflow.py        # End-to-end integration tests across all formats
│   ├── test_generation.py          # Document generation and round-trip verification tests
│   ├── test_ingestion.py           # File gate and document extraction tests
│   ├── test_interview.py           # State machine progression and correction tests
│   ├── test_logger.py              # PII and API key redaction tests
│   └── test_validation.py          # Deterministic validator unit tests
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.11 or 3.12
- Git

### 2. Environment Setup
```bash
# Clone or navigate to the repository
cd "c:/Users/yoges/Desktop/Sarvam AI"

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file from `.env.example` or configure `.streamlit/secrets.toml`:
```ini
SARVAM_API_KEY=your_actual_sarvam_api_key_here
```
*(Note: If no API key is set, the application automatically uses high-fidelity offline mock adapters, allowing full offline testing and UI evaluation without consuming API credits).*

### 4. Run Smoke Check
```bash
python scripts/smoke_test.py
```

### 5. Launch the Streamlit Application
```bash
streamlit run app/main.py
```
Open `http://localhost:8501` in your browser.

---

## 🧪 Running Automated Tests

Run the full automated test suite:
```bash
pytest -v
```

All 25 automated tests verify:
- Aadhaar Verhoeff checksum calculation, rejection of invalid lengths or prefixes, and log masking.
- Indian mobile number validation, 10-digit requirement, and separator stripping.
- Calendar date validation, DOB future-date rejection, and DD/MM/YYYY formatting.
- File gate security (magic bytes check, rejection of malicious extensions or empty files).
- Multi-format document extraction across DOCX, AcroForm PDF, and Flat PDF.
- State machine progression: required field gating, skip logic for optional fields, navigation back for edits.
- Document generation across all 3 formats with 100% round-trip verification.

---

## 🔒 Security & Privacy Practices

- **Zero Secret Leakage:** API credentials are never printed to terminal, written to logs, or committed to Git.
- **Strict Gitignore:** Guards `.env`, `.streamlit/secrets.toml`, uploads, outputs, and caches.
- **Untrusted Document Boundary:** Document content is placed strictly within tagged data delimiters and never executed as prompt instructions.
- **Ephemeral Session Data:** Uploads and generated documents are stored only for the duration of the form session and shredded upon completion.
