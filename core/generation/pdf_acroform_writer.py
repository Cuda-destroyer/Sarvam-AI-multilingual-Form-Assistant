"""
AcroForm PDF Writer.
Populates interactive form fields using pypdf, maintaining existing PDF layout and appearance.
"""

import io
from pathlib import Path
from typing import BinaryIO, Dict, Union
from pypdf import PdfReader, PdfWriter
from core.models import FieldState, FieldValue, FormSchema
from core.privacy.logger import get_logger

logger = get_logger("pdf_acroform_writer")


class PdfAcroFormWriter:
    """Populates interactive AcroForm fields in PDF documents."""

    def populate_form(
        self,
        template_bytes_or_path: Union[bytes, Path, str, BinaryIO],
        schema: FormSchema,
        values: Dict[str, FieldValue],
        output_path: Path,
    ) -> Path:
        """
        Fill interactive fields in the PDF template.
        """
        if isinstance(template_bytes_or_path, (str, Path)):
            reader = PdfReader(str(template_bytes_or_path))
        elif isinstance(template_bytes_or_path, bytes):
            reader = PdfReader(io.BytesIO(template_bytes_or_path))
        else:
            reader = PdfReader(template_bytes_or_path)

        writer = PdfWriter()
        writer.append(reader)

        # Build dictionary of {field_name: value}
        field_dict = {}
        for field in schema.fields:
            val = values.get(field.id)
            if not val or val.state != FieldState.CONFIRMED or not val.confirmed_value:
                continue

            if field.anchor and field.anchor.field_name:
                field_dict[field.anchor.field_name] = val.confirmed_value

        # Update all pages with matching fields
        for page in writer.pages:
            writer.update_page_form_field_values(page, field_dict)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

        logger.info("Successfully populated AcroForm PDF at: %s with %d values.", output_path, len(field_dict))
        return output_path
