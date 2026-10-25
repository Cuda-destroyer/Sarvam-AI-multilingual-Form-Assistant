# Privacy Notice & Data Handling Architecture

**Effective Date:** 2026-10-25  
**Application:** Sarvam AI-Powered Multilingual Form and Document Filling Assistant

---

## 1. Core Privacy Commitments

1. **Data Minimization:** We collect only the information requested by your uploaded form. No secondary tracking, demographic profiling, or advertising data is gathered.
2. **Third-Party Processing Disclosure:** Speech-to-text, translation, and language understanding requests are processed through Sarvam AI's REST APIs. Audio clips are restricted to a maximum of 30 seconds.
3. **Sensitive Identifier Protection:**
   - Aadhaar numbers are never logged in full, never displayed in plain text (`XXXX-XXXX-NNNN` masking), and never sent in free-form LLM contexts.
   - Mobile numbers and financial details are kept strictly in localized session memory.
4. **No Permanent Retention in MVP:**
   - Uploaded files, temporary audio recordings, and generated documents reside in ephemeral session storage.
   - Clicking "Finish & Wipe Data" or ending the session initiates immediate file shredding.
5. **No AI Training on Private Submissions:** Data processed through the application's API integrations is not used to train global AI models without consent.
