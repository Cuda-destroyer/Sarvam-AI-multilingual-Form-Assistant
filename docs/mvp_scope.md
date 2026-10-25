# MVP Scope & Acceptance Scenarios

**Project:** Sarvam Multilingual Form & Document Filler  
**Document Version:** 1.0  
**Date:** 2026-10-25

---

## 1. MVP Boundaries

### In Scope for MVP:
1. **Document Inputs:**
   - Microsoft Word (`.docx`) forms with tables, text paragraphs, underscores, and fill blanks.
   - Adobe PDF (`.pdf`) forms with both:
     - Interactive form fields (AcroForms).
     - Flat text forms with lines/underscores populated via coordinate overlays.
2. **Supported Languages:**
   - Primary MVP: **Hindi (`hi-IN`)**, **Marathi (`mr-IN`)**, **Tamil (`ta-IN`)**, **English (`en-IN`)**.
   - Extensible language catalog with fallback to English where models require it.
3. **Conversational Interview:**
   - One question at a time.
   - Spoken question audio (Bulbul v3 TTS) when available.
   - Spoken answer input (Saaras v3 STT via browser recording with max 30s audio cap) + robust text input fallback.
   - Deterministic answer parsing first (digits, dates, options) followed by schema-constrained LLM interpretation.
   - Read-back confirmation for every value with user consent.
   - Correction, Repeat, Back, and Skip (for optional fields) navigation.
4. **Deterministic Validation:**
   - Aadhaar: 12 digits, Verhoeff checksum algorithm, masking in UI/logs (`XXXX-XXXX-1234`).
   - Mobile: 10 digits starting with 6-9, stripping prefix +91/0.
   - Date of Birth: valid calendar date, rejection of future dates, standard DD/MM/YYYY formatting.
   - Name: transliteration to Latin script (no semantic translation), letter-by-letter review.
   - Pin code: exactly 6 digits.
   - Choices & Enumerations: strict mapping to allowed form options.
5. **Output Generation & Round-Trip Verification:**
   - DOCX generation preserving formatting, styles, and tables.
   - AcroForm generation populating form fields.
   - Flat PDF generation using ReportLab overlays.
   - **Mandatory Round-Trip Verification:** re-extracting text from generated files to prove 100% of confirmed values are present.
6. **Privacy & Security:**
   - Redacting logger filtering sensitive PII (Aadhaar, phones) and credentials.
   - Zero hardcoded keys; secure `.env` and `st.secrets` support.
   - Session isolation and automatic file cleanup upon session termination.

### Explicitly Out of Scope for MVP (Backlogged for Phase 12):
- Scanned handwriting OCR requiring specialized manual layout reconstruction.
- Real Aadhaar authentication / UIDAI e-KYC (only format and checksum validation is supported).
- Cloud storage persistence across different devices without local browser session.
- Automatic forging of physical signatures, official seals, or stamps.

---

## 2. 10 Acceptance Scenarios

1. **Scenario 1 (Document Upload & Gate):** User uploads a valid 2-page DOCX or PDF form. The system accepts it, validates magic bytes, and extracts structure without error. An invalid `.exe` or oversized file is cleanly rejected with a plain-language explanation.
2. **Scenario 2 (Form Summary & Understanding):** The system displays document title, estimated fields, and asks for confirmation before initiating questions.
3. **Scenario 3 (Language Selection):** User switches language to Hindi (`hi-IN`). All subsequent questions and prompts are rendered in Hindi while the form target remains English.
4. **Scenario 4 (Aadhaar Validation & Masking):** User enters an invalid 11-digit Aadhaar or one with an invalid Verhoeff checksum. The system rejects it with an explanatory message. When a valid 12-digit number is provided, it is masked as `XXXX-XXXX-NNNN` in the UI and logs.
5. **Scenario 5 (Voice Input with Text Fallback):** User records a 15-second voice response in Hindi. If voice recording is unavailable or fails, user smoothly types the answer in the text fallback field.
6. **Scenario 6 (Name Transliteration):** User speaks their name "राजेश शर्मा". The system transliterates it to "Rajesh Sharma" (not translating "Sharma" semantically) and prompts the user to confirm the Latin spelling.
7. **Scenario 7 (Date Parsing & Normalization):** User provides natural language date (e.g., "15 अगस्त 1995"). The system converts it deterministically to `15/08/1995` and verifies it is a valid past calendar date.
8. **Scenario 8 (Review & In-Place Correction):** On the review screen, the user inspects all collected fields, identifies a typo in their mobile number, navigates back to edit it, and confirms the updated value.
9. **Scenario 9 (Round-Trip Verified Generation):** User triggers generation. The system fills the document, parses the generated output file, verifies all confirmed answers exist in the output, and produces a green verification badge before offering the download.
10. **Scenario 10 (Session Wipe & Privacy):** User clicks "Finish & Wipe Data". All session states, uploaded temp files, and generated documents are deleted immediately.
