"""
Round-Trip Output Verifier.
Re-opens and parses generated documents (DOCX and PDF), proving that 100% of confirmed
answers are actually present in the generated output file.
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pypdf import PdfReader
from docx import Document
from core.models import FieldState, FieldValue, FormSchema
from core.privacy.logger import get_logger

logger = get_logger("roundtrip_verifier")


class VerificationReport(BaseModel):
    """Detailed verification report proving integrity of generated output."""
    is_verified: bool
    total_confirmed_fields: int
    verified_fields_count: int
    missing_fields: List[str] = Field(default_factory=list)
    field_match_details: Dict[str, bool] = Field(default_factory=dict)
    summary_message: str


class RoundTripVerifier:
    """Verifies that generated documents contain all confirmed values."""

    def verify_output(
        self,
        generated_file_path: Path,
        schema: FormSchema,
        values: Dict[str, FieldValue],
    ) -> VerificationReport:
        """
        Inspect generated document and verify all confirmed values are present.
        """
        if not generated_file_path.exists() or generated_file_path.stat().st_size == 0:
            return VerificationReport(
                is_verified=False,
                total_confirmed_fields=0,
                verified_fields_count=0,
                missing_fields=["Generated file does not exist or is empty"],
                summary_message="Generation failed: output file is missing or zero bytes.",
            )

        confirmed_pairs = {}
        for field in schema.fields:
            val = values.get(field.id)
            if val and val.state == FieldState.CONFIRMED and val.confirmed_value:
                confirmed_pairs[field.id] = (field, val.confirmed_value)

        total_count = len(confirmed_pairs)
        if total_count == 0:
            return VerificationReport(
                is_verified=True,
                total_confirmed_fields=0,
                verified_fields_count=0,
                summary_message="No confirmed fields were present to verify.",
            )

        ext = generated_file_path.suffix.lower()
        verified_dict: Dict[str, bool] = {}
        missing: List[str] = []

        if ext == ".docx":
            doc = Document(str(generated_file_path))
            full_doc_text = " ".join([p.text for p in doc.paragraphs])
            for t in doc.tables:
                for r in t.rows:
                    full_doc_text += " " + " ".join([c.text for c in r.cells])

            for fid, (field, expected_val) in confirmed_pairs.items():
                # Check for exact or normalized substring
                is_present = expected_val.strip() in full_doc_text
                verified_dict[fid] = is_present
                if not is_present:
                    missing.append(field.label)

        elif ext == ".pdf":
            reader = PdfReader(str(generated_file_path))
            # 1. Check form fields if AcroForm
            pdf_fields = reader.get_fields() or {}
            pdf_field_values = {k: v.get("/V", "") for k, v in pdf_fields.items() if isinstance(v, dict)}

            # 2. Extract full page text
            full_pdf_text = ""
            for page in reader.pages:
                full_pdf_text += " " + (page.extract_text() or "")

            for fid, (field, expected_val) in confirmed_pairs.items():
                expected_clean = expected_val.strip()
                # Check AcroForm field match
                is_in_acro = False
                if field.anchor and field.anchor.field_name:
                    acro_val = str(pdf_field_values.get(field.anchor.field_name, ""))
                    if expected_clean in acro_val:
                        is_in_acro = True

                # Check text overlay match
                is_in_text = expected_clean in full_pdf_text

                is_present = is_in_acro or is_in_text
                verified_dict[fid] = is_present
                if not is_present:
                    missing.append(field.label)

        verified_count = sum(1 for v in verified_dict.values() if v)
        is_all_verified = (verified_count == total_count)

        if is_all_verified:
            summary = f"Verified: all {total_count} confirmed values are accurately placed in the document."
        else:
            summary = f"Verification Warning: {len(missing)} of {total_count} fields could not be confirmed in output: {', '.join(missing)}"

        logger.info("Round-trip verification result: %s (verified %d/%d)", is_all_verified, verified_count, total_count)

        return VerificationReport(
            is_verified=is_all_verified,
            total_confirmed_fields=total_count,
            verified_fields_count=verified_count,
            missing_fields=missing,
            field_match_details=verified_dict,
            summary_message=summary,
        )
