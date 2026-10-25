"""
Document File Gate: Security & format validation for all uploaded documents.
Validates file extensions, magic bytes, size limits, page counts, and prevents path traversal.
"""

from pathlib import Path
import re
from typing import BinaryIO, Optional, Tuple, Union
from pypdf import PdfReader
from docx import Document
from core.config import get_config
from core.privacy.logger import get_logger

logger = get_logger("file_gate")

# Magic bytes
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"


class FileGateError(Exception):
    """User-facing safe error message explaining file validation failure."""
    pass


class DocumentFileGate:
    """Validates uploaded files before ingestion."""

    def __init__(self):
        self.config = get_config()
        self.max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        self.max_pages = 15

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal or unsafe characters."""
        clean = Path(filename).name
        # Keep only alphanumeric, hyphens, underscores, and dots
        clean = re.sub(r"[^\w\-. ]", "_", clean)
        return clean.strip() or "uploaded_form"

    def validate_file(self, file_path_or_bytes: Union[str, Path, bytes, BinaryIO], filename: str) -> Tuple[str, int]:
        """
        Validate file for format integrity, size, and page count.
        
        Returns:
            Tuple of (detected_format, page_count) where detected_format is 'pdf' or 'docx'.
        Raises:
            FileGateError if validation fails.
        """
        safe_name = self.sanitize_filename(filename)
        ext = safe_name.lower().split(".")[-1] if "." in safe_name else ""

        if ext not in self.config.allowed_extensions:
            raise FileGateError(
                f"Unsupported file format '.{ext}'. Please upload a PDF (.pdf) or Word document (.docx)."
            )

        # Read content bytes
        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                content = f.read()
        elif isinstance(file_path_or_bytes, bytes):
            content = file_path_or_bytes
        else:
            content = file_path_or_bytes.read()
            if hasattr(file_path_or_bytes, "seek"):
                file_path_or_bytes.seek(0)

        # Check size
        size_bytes = len(content)
        if size_bytes == 0:
            raise FileGateError("The uploaded file is empty. Please select a valid document.")

        if size_bytes > self.max_size_bytes:
            raise FileGateError(
                f"The file size ({size_bytes / (1024*1024):.1f} MB) exceeds the allowed limit of {self.config.max_file_size_mb} MB."
            )

        # Check magic bytes and page count
        if ext == "pdf":
            if not content.startswith(PDF_MAGIC):
                raise FileGateError("The file does not appear to be a valid PDF document (invalid file header).")

            try:
                import io
                reader = PdfReader(io.BytesIO(content))
                page_count = len(reader.pages)
                if page_count == 0:
                    raise FileGateError("The PDF document contains no pages.")
                if page_count > self.max_pages:
                    raise FileGateError(
                        f"Document has {page_count} pages, which exceeds the supported limit of {self.max_pages} pages."
                    )
                return ("pdf", page_count)
            except Exception as e:
                if isinstance(e, FileGateError):
                    raise
                raise FileGateError(f"Unable to read PDF document: corrupted or encrypted ({str(e)}).")

        elif ext == "docx":
            if not content.startswith(ZIP_MAGIC):
                raise FileGateError("The file does not appear to be a valid Word (.docx) document.")

            try:
                import io
                doc = Document(io.BytesIO(content))
                # Approximate page count for docx
                para_count = len(doc.paragraphs)
                table_count = len(doc.tables)
                if para_count == 0 and table_count == 0:
                    raise FileGateError("The Word document has no text or tables.")
                # Estimated pages based on paragraphs/tables
                est_pages = max(1, (para_count + table_count * 3) // 25 + 1)
                return ("docx", est_pages)
            except Exception as e:
                if isinstance(e, FileGateError):
                    raise
                raise FileGateError(f"Unable to open Word document: corrupted or unsupported format ({str(e)}).")

        raise FileGateError(f"Unsupported document format: {ext}")
