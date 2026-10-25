"""
Flat-Text PDF Extractor with Coordinate Detection.
Uses pdfplumber to extract text lines, locate underscores / blanks,
and anchor fields to precise (x, y) coordinates for later overlay generation.
"""

import io
from pathlib import Path
import re
from typing import BinaryIO, List, Tuple, Union
import pdfplumber
from core.ingestion.docx_reader import infer_field_type_from_label, slugify_label
from core.models import DestinationAnchor, FieldSpec, FieldType
from core.privacy.logger import get_logger

logger = get_logger("pdf_text")

LABEL_BLANK_RE = re.compile(
    r"([A-Za-z0-9\s/().]+?)[:：]?\s*([_]{3,}|\[\s*\]|\.{4,})",
)


class PdfTextExtractor:
    """Extracts fields and geometrical coordinates from flat text PDFs."""

    def extract_fields(self, pdf_bytes_or_path: Union[bytes, Path, str, BinaryIO]) -> List[FieldSpec]:
        """
        Scan flat PDF pages, finding labels and blanks with page coordinates.
        """
        fields: List[FieldSpec] = []
        field_counter = 0

        # Open with pdfplumber
        if isinstance(pdf_bytes_or_path, (str, Path)):
            pdf_ctx = pdfplumber.open(str(pdf_bytes_or_path))
        elif isinstance(pdf_bytes_or_path, bytes):
            pdf_ctx = pdfplumber.open(io.BytesIO(pdf_bytes_or_path))
        else:
            pdf_ctx = pdfplumber.open(pdf_bytes_or_path)

        with pdf_ctx as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_height = float(page.height)
                # Extract words to inspect text and coordinates
                words = page.extract_words(keep_blank_chars=False)
                text = page.extract_text() or ""

                # Find line matches
                lines = text.split("\n")
                for line in lines:
                    match = LABEL_BLANK_RE.search(line)
                    if match:
                        label_candidate = match.group(1).strip()
                        # Clean label from leading numbers like "1. Name"
                        clean_label = re.sub(r"^\d+[\.\)]\s*", "", label_candidate).strip()
                        if 2 < len(clean_label) < 45:
                            field_counter += 1
                            ftype, handling, opts = infer_field_type_from_label(clean_label)
                            fid = slugify_label(clean_label, field_counter)

                            # Find approximate word coordinates on the page
                            matching_words = [w for w in words if clean_label.split()[0].lower() in w["text"].lower()]
                            if matching_words:
                                ref_word = matching_words[0]
                                # Coordinates for overlay: slightly to the right of label
                                # Note: ReportLab origin is bottom-left; pdfplumber is top-left
                                x_pos = float(ref_word["x1"]) + 15.0
                                # Invert Y for ReportLab (ReportLab Y = page_height - pdfplumber_top - font_offset)
                                y_pos = page_height - float(ref_word["top"]) - 10.0
                            else:
                                x_pos = 150.0
                                y_pos = page_height - (field_counter * 35.0)

                            anchor = DestinationAnchor(
                                target_type="pdf_overlay",
                                page_number=page_idx,
                                x=x_pos,
                                y=y_pos,
                                font_size=10.0,
                            )

                            spec = FieldSpec(
                                id=fid,
                                label=clean_label,
                                field_type=ftype,
                                handling=handling,
                                options=opts,
                                anchor=anchor,
                                display_order=field_counter,
                            )
                            fields.append(spec)

        logger.info("Flat PDF extractor found %d fields with coordinates.", len(fields))
        return fields
