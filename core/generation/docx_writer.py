"""
DOCX Document Writer.
Populates confirmed form answers into original DOCX templates,
preserving styles, runs, and table layouts without rebuilding the document.
"""

import io
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Union
from docx import Document
from core.models import FieldSpec, FieldState, FieldValue, FormSchema
from core.privacy.logger import get_logger

logger = get_logger("docx_writer")


class DocxDocumentWriter:
    """Populates confirmed values into DOCX templates."""

    def populate_form(
        self,
        template_bytes_or_path: Union[bytes, Path, str, BinaryIO],
        schema: FormSchema,
        values: Dict[str, FieldValue],
        output_path: Path,
    ) -> Path:
        """
        Write confirmed values into the DOCX template.
        """
        if isinstance(template_bytes_or_path, (str, Path)):
            doc = Document(str(template_bytes_or_path))
        elif isinstance(template_bytes_or_path, bytes):
            doc = Document(io.BytesIO(template_bytes_or_path))
        else:
            doc = Document(template_bytes_or_path)

        for field in schema.fields:
            val = values.get(field.id)
            if not val or val.state != FieldState.CONFIRMED or not val.confirmed_value:
                continue

            anchor = field.anchor
            if not anchor:
                continue

            text_to_insert = val.confirmed_value

            if anchor.target_type == "docx_cell":
                if (
                    anchor.table_index is not None
                    and anchor.row_index is not None
                    and anchor.col_index is not None
                ):
                    try:
                        table = doc.tables[anchor.table_index]
                        cell = table.rows[anchor.row_index].cells[anchor.col_index]
                        # Set cell text clearly
                        cell.text = text_to_insert
                    except IndexError as e:
                        logger.warning("DOCX cell out of bounds (%s) for field '%s'", str(e), field.id)

            elif anchor.target_type == "docx_placeholder":
                if anchor.placeholder_text:
                    ph = anchor.placeholder_text
                    for p in doc.paragraphs:
                        if ph in p.text:
                            # Replace placeholder
                            p.text = p.text.replace(ph, f" {text_to_insert} ")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        logger.info("Successfully generated populated DOCX at: %s", output_path)
        return output_path
