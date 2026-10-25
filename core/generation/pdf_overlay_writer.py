"""
Flat PDF Coordinate Overlay Writer.
Draws confirmed answers at exact (x, y) coordinates using ReportLab,
then merges overlays onto original PDF pages using pypdf.
"""

import io
from pathlib import Path
from typing import BinaryIO, Dict, Union
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from core.models import FieldState, FieldValue, FormSchema
from core.privacy.logger import get_logger

logger = get_logger("pdf_overlay_writer")


class PdfOverlayWriter:
    """Draws coordinate text overlays on flat text PDFs."""

    def populate_form(
        self,
        template_bytes_or_path: Union[bytes, Path, str, BinaryIO],
        schema: FormSchema,
        values: Dict[str, FieldValue],
        output_path: Path,
    ) -> Path:
        """
        Merge text overlays at anchored coordinates for each page.
        """
        if isinstance(template_bytes_or_path, (str, Path)):
            reader = PdfReader(str(template_bytes_or_path))
        elif isinstance(template_bytes_or_path, bytes):
            reader = PdfReader(io.BytesIO(template_bytes_or_path))
        else:
            reader = PdfReader(template_bytes_or_path)

        writer = PdfWriter()

        # Group field values by page number
        page_fields: Dict[int, list] = {}
        for field in schema.fields:
            val = values.get(field.id)
            if not val or val.state != FieldState.CONFIRMED or not val.confirmed_value:
                continue

            anchor = field.anchor
            if not anchor or anchor.target_type != "pdf_overlay":
                continue

            page_num = anchor.page_number or 1
            if page_num not in page_fields:
                page_fields[page_num] = []
            page_fields[page_num].append((field, val))

        # Process each page
        for page_idx, orig_page in enumerate(reader.pages, start=1):
            if page_idx in page_fields:
                # Create ReportLab overlay buffer for this page
                packet = io.BytesIO()
                page_width = float(orig_page.mediabox.width)
                page_height = float(orig_page.mediabox.height)

                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                can.setFont("Helvetica-Bold", 10)
                can.setFillColorRGB(0.05, 0.1, 0.4)  # Professional dark blue text for filled values

                for field, val in page_fields[page_idx]:
                    x = field.anchor.x or 150.0
                    y = field.anchor.y or 100.0
                    text = val.confirmed_value

                    # Print value cleanly
                    can.drawString(x, y, text)

                can.save()
                packet.seek(0)

                overlay_pdf = PdfReader(packet)
                overlay_page = overlay_pdf.pages[0]
                orig_page.merge_page(overlay_page)

            writer.add_page(orig_page)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

        logger.info("Successfully generated overlaid flat PDF at: %s", output_path)
        return output_path
