"""
Form Schema Builder.
Assembles validated FormSchema instances from uploaded documents, coordinating
file validation, document parsing, field typing, and multilingual explanations.
"""

from pathlib import Path
from typing import BinaryIO, List, Optional, Union
import uuid
from core.ingestion.docx_reader import DocxFormReader
from core.ingestion.file_gate import DocumentFileGate, FileGateError
from core.ingestion.pdf_acroform import PdfAcroFormReader
from core.ingestion.pdf_text import PdfTextExtractor
from core.models import FieldSpec, FormSchema
from core.privacy.logger import get_logger
from core.services.sarvam.llm import LLMService

logger = get_logger("schema_builder")


class SchemaBuilder:
    """Orchestrates document ingestion and builds FormSchema."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.file_gate = DocumentFileGate()
        self.docx_reader = DocxFormReader()
        self.acroform_reader = PdfAcroFormReader()
        self.pdf_text_extractor = PdfTextExtractor()
        self.llm_service = llm_service

    def build_schema(
        self,
        file_bytes_or_path: Union[bytes, Path, str, BinaryIO],
        original_filename: str,
    ) -> FormSchema:
        """
        Validate, parse document, and construct a complete FormSchema.
        """
        # Step 1: Validate file gate
        detected_format, page_count = self.file_gate.validate_file(file_bytes_or_path, original_filename)
        clean_name = self.file_gate.sanitize_filename(original_filename)

        source_type = detected_format
        fields: List[FieldSpec] = []

        # Step 2: Extract fields based on document characteristics
        if detected_format == "docx":
            source_type = "docx"
            fields = self.docx_reader.extract_fields(file_bytes_or_path)

        elif detected_format == "pdf":
            # Check if AcroForm or Flat PDF
            if self.acroform_reader.is_acroform(file_bytes_or_path):
                source_type = "pdf_acroform"
                fields = self.acroform_reader.extract_fields(file_bytes_or_path)
            else:
                source_type = "pdf_flat"
                fields = self.pdf_text_extractor.extract_fields(file_bytes_or_path)

        # Step 3: Populate multilingual explanations for each field
        for field in fields:
            self._enrich_field_explanations(field)

        # Title formatting
        title = clean_name.rsplit(".", 1)[0].replace("_", " ").title()

        form_id = f"form_{uuid.uuid4().hex[:8]}"
        schema = FormSchema(
            form_id=form_id,
            title=title,
            source_type=source_type,
            original_filename=clean_name,
            page_count=page_count,
            fields=fields,
        )

        logger.info(
            "Constructed FormSchema '%s' (type=%s, fields=%d, pages=%d)",
            schema.title,
            schema.source_type,
            len(schema.fields),
            schema.page_count,
        )
        return schema

    def _enrich_field_explanations(self, field: FieldSpec) -> None:
        """Populate initial multilingual explanations for the field."""
        llm = self.llm_service or LLMService()
        for lang in ["en-IN", "hi-IN", "mr-IN", "ta-IN"]:
            if lang not in field.explanation:
                field.explanation[lang] = llm.generate_question_prompt(field, lang)
