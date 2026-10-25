"""
AcroForm PDF Extractor.
Extracts interactive fillable fields from PDF documents using pypdf.
"""

import io
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union
from pypdf import PdfReader
from core.ingestion.docx_reader import infer_field_type_from_label, slugify_label
from core.models import DestinationAnchor, FieldSpec, FieldType, HandlingMode
from core.privacy.logger import get_logger

logger = get_logger("pdf_acroform")


class PdfAcroFormReader:
    """Extracts interactive AcroForm fields from fillable PDFs."""

    def is_acroform(self, pdf_bytes_or_path: Union[bytes, Path, str, BinaryIO]) -> bool:
        """Check if PDF contains interactive form fields."""
        try:
            if isinstance(pdf_bytes_or_path, (str, Path)):
                reader = PdfReader(str(pdf_bytes_or_path))
            elif isinstance(pdf_bytes_or_path, bytes):
                reader = PdfReader(io.BytesIO(pdf_bytes_or_path))
            else:
                reader = PdfReader(pdf_bytes_or_path)

            fields = reader.get_fields()
            return bool(fields and len(fields) > 0)
        except Exception:
            return False

    def extract_fields(self, pdf_bytes_or_path: Union[bytes, Path, str, BinaryIO]) -> List[FieldSpec]:
        """
        Extract interactive fields into structured FieldSpecs with pdf_acroform anchors.
        """
        if isinstance(pdf_bytes_or_path, (str, Path)):
            reader = PdfReader(str(pdf_bytes_or_path))
        elif isinstance(pdf_bytes_or_path, bytes):
            reader = PdfReader(io.BytesIO(pdf_bytes_or_path))
        else:
            reader = PdfReader(pdf_bytes_or_path)

        raw_fields = reader.get_fields() or {}
        specs: List[FieldSpec] = []

        counter = 0
        for field_name, field_info in raw_fields.items():
            counter += 1
            # Clean display label
            clean_label = field_name.replace("_", " ").title()

            # Determine field type
            field_type_val = field_info.get("/FT", "")
            ftype, handling, options = infer_field_type_from_label(clean_label)

            if field_type_val == "/Btn":
                # Checkbox or Radio button
                ftype = FieldType.CHOICE
                options = ["Yes", "No"]
            elif field_type_val == "/Ch":
                ftype = FieldType.CHOICE
                opt_values = field_info.get("/Opt", [])
                if opt_values:
                    options = [str(o) for o in opt_values]

            anchor = DestinationAnchor(
                target_type="pdf_acroform",
                field_name=field_name,
            )

            spec = FieldSpec(
                id=slugify_label(field_name, counter),
                label=clean_label,
                field_type=ftype,
                handling=handling,
                options=options,
                anchor=anchor,
                display_order=counter,
            )
            specs.append(spec)

        logger.info("AcroForm reader found %d interactive fields in PDF.", len(specs))
        return specs
