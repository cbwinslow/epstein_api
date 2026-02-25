"""
Processing schemas for validated input/output.

These Pydantic models ensure all processing outputs are strictly validated.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExtractionMethod(str, Enum):
    """Method used for text extraction."""

    PYMUPDF = "PyMuPDF"
    PDFPLUMBER = "pdfplumber"
    TESSERACT_OCR = "Tesseract_OCR"
    SURYA_OCR = "Surya_OCR"
    WHISPER_TRANSCRIPTION = "Whisper"
    MANUAL = "manual"


class ProcessingStatus(str, Enum):
    """Status of document processing."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED_PROCESSING = "FAILED_PROCESSING"
    FAILED_OCR = "FAILED_OCR"


class ProcessedDocumentSchema(BaseModel):
    """Validated schema for processed document JSON sidecar.

    This ensures all processed documents have consistent metadata
    before being used by downstream systems.
    """

    model_config = {"extra": "forbid"}

    original_file_id: int
    original_filename: str
    raw_text: str = Field(..., min_length=0)
    extraction_method: ExtractionMethod
    page_count: int | None = None
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    text_density: float | None = None
    character_count: int = 0
    word_count: int = 0
    language_detected: str | None = None
    errors: list[str] = Field(default_factory=list)

    @field_validator("character_count", "page_count", mode="before")
    @classmethod
    def validate_positive(cls, v: Any) -> int | None:
        """Ensure values are non-negative."""
        if v is None:
            return None
        return max(0, int(v))

    def is_scanned(self) -> bool:
        """Determine if document is likely scanned based on text density."""
        if self.page_count and self.page_count > 0:
            avg_chars_per_page = self.character_count / self.page_count
            return avg_chars_per_page < 100
        return self.extraction_method in (
            ExtractionMethod.TESSERACT_OCR,
            ExtractionMethod.SURYA_OCR,
        )


class ProcessingRequest(BaseModel):
    """Request to process a document."""

    model_config = {"extra": "forbid"}

    file_id: int = Field(..., gt=0)
    force_ocr: bool = False
    language: str | None = None


class ProcessingResult(BaseModel):
    """Result of document processing."""

    model_config = {"extra": "forbid"}

    file_id: int
    status: ProcessingStatus
    json_sidecar_path: str | None = None
    extraction_method: ExtractionMethod | None = None
    character_count: int = 0
    word_count: int = 0
    page_count: int | None = None
    error_message: str | None = None
    processing_time_seconds: float | None = None
