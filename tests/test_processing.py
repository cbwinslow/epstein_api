"""
Unit tests for processing module.

Tests the router, extractors, and sidecar functionality.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.processing.router import (
    ProcessingRoute,
    calculate_text_density,
    detect_file_type,
    route_file,
    should_use_ocr,
)
from backend.core.processing.schemas import (
    ExtractionMethod,
    ProcessedDocumentSchema,
    ProcessingStatus,
)
from backend.core.processing.sidecar import (
    delete_sidecar,
    generate_sidecar_path,
    load_json_sidecar,
    save_json_sidecar,
    sidecar_exists,
)


class TestFileTypeDetection:
    """Tests for file type detection."""

    def test_detect_pdf(self) -> None:
        """Test PDF detection."""
        assert detect_file_type(Path("document.pdf")) == "pdf"
        assert detect_file_type(Path("document.PDF")) == "pdf"

    def test_detect_image(self) -> None:
        """Test image detection."""
        assert detect_file_type(Path("image.jpg")) == "image"
        assert detect_file_type(Path("image.png")) == "image"
        assert detect_file_type(Path("photo.JPEG")) == "image"

    def test_detect_audio(self) -> None:
        """Test audio detection."""
        assert detect_file_type(Path("audio.mp3")) == "audio"
        assert detect_file_type(Path("sound.wav")) == "audio"

    def test_detect_video(self) -> None:
        """Test video detection."""
        assert detect_file_type(Path("video.mp4")) == "video"
        assert detect_file_type(Path("movie.mov")) == "video"


class TestTextDensity:
    """Tests for text density calculation."""

    def test_calculate_text_density(self) -> None:
        """Test text density calculation."""
        text = "Hello world " * 100
        density = calculate_text_density(text, 10)
        assert density > 0

    def test_zero_pages(self) -> None:
        """Test density with zero pages."""
        density = calculate_text_density("text", 0)
        assert density == 0.0


class TestOCRDecision:
    """Tests for OCR decision logic."""

    def test_force_ocr(self) -> None:
        """Test force OCR flag."""
        assert should_use_ocr("some text", 10, force_ocr=True) is True

    def test_low_text_density_triggers_ocr(self) -> None:
        """Test low text density triggers OCR."""
        low_text = "abc"
        assert should_use_ocr(low_text, 10, force_ocr=False) is True

    def test_high_text_density_skips_ocr(self) -> None:
        """Test high text density skips OCR."""
        high_text = "This is a long text " * 200
        assert should_use_ocr(high_text, 10, force_ocr=False) is False


class TestRouter:
    """Tests for file routing."""

    def test_pdf_routes_to_native(self) -> None:
        """Test PDF routes to native extraction."""
        route = route_file(Path("document.pdf"))
        assert route == ProcessingRoute.NATIVE_PDF

    def test_pdf_with_low_density_routes_to_ocr(self) -> None:
        """Test low density PDF routes to OCR."""
        route = route_file(
            Path("scanned.pdf"),
            initial_text="short",
            page_count=10,
        )
        assert route == ProcessingRoute.OCR_PDF

    def test_image_routes_to_ocr(self) -> None:
        """Test image routes to OCR."""
        route = route_file(Path("image.jpg"))
        assert route == ProcessingRoute.OCR_IMAGE

    def test_audio_routes_to_media(self) -> None:
        """Test audio routes to media."""
        route = route_file(Path("audio.mp3"))
        assert route == ProcessingRoute.MEDIA_AUDIO


class TestProcessedDocumentSchema:
    """Tests for Pydantic schema validation."""

    def test_valid_schema(self) -> None:
        """Test creating valid schema."""
        doc = ProcessedDocumentSchema(
            original_file_id=1,
            original_filename="test.pdf",
            raw_text="Extracted text",
            extraction_method=ExtractionMethod.PYMUPDF,
            page_count=10,
        )
        assert doc.original_file_id == 1
        assert doc.character_count == 14

    def test_is_scanned_method(self) -> None:
        """Test is_scanned detection."""
        scanned = ProcessedDocumentSchema(
            original_file_id=1,
            original_filename="scanned.pdf",
            raw_text="short",
            extraction_method=ExtractionMethod.TESSERACT_OCR,
            page_count=10,
            character_count=50,
        )
        assert scanned.is_scanned() is True

    def test_not_scanned_with_native(self) -> None:
        """Test not scanned with native extraction."""
        doc = ProcessedDocumentSchema(
            original_file_id=1,
            original_filename="text.pdf",
            raw_text="Full text " * 500,
            extraction_method=ExtractionMethod.PYMUPDF,
            page_count=10,
            character_count=5000,
        )
        assert doc.is_scanned() is False


class TestJSONSidecar:
    """Tests for JSON sidecar operations."""

    def test_generate_sidecar_path(self) -> None:
        """Test sidecar path generation."""
        original = Path("/data/document.pdf")
        sidecar = generate_sidecar_path(original)
        assert sidecar == Path("/data/document_processed.json")

    def test_save_and_load_sidecar(
        self,
        temp_data_dir: Path,
    ) -> None:
        """Test saving and loading sidecar."""
        doc = ProcessedDocumentSchema(
            original_file_id=1,
            original_filename="test.pdf",
            raw_text="Test text",
            extraction_method=ExtractionMethod.PYMUPDF,
            page_count=1,
        )

        original_path = temp_data_dir / "test.pdf"
        original_path.touch()

        sidecar_path = save_json_sidecar(original_path, doc)

        assert sidecar_path.exists()

        loaded = load_json_sidecar(sidecar_path)
        assert loaded.original_file_id == 1
        assert loaded.raw_text == "Test text"

    def test_sidecar_exists(self, temp_data_dir: Path) -> None:
        """Test sidecar existence check."""
        path = temp_data_dir / "doc.pdf"
        path.touch()

        assert sidecar_exists(path) is False

        sidecar = generate_sidecar_path(path)
        sidecar.write_text("{}")

        assert sidecar_exists(path) is True

    def test_delete_sidecar(self, temp_data_dir: Path) -> None:
        """Test sidecar deletion."""
        path = temp_data_dir / "doc.pdf"
        path.touch()

        sidecar = generate_sidecar_path(path)
        sidecar.write_text("{}")

        assert delete_sidecar(path) is True
        assert not sidecar.exists()


class TestProcessingResult:
    """Tests for processing result schemas."""

    def test_processing_status_values(self) -> None:
        """Test processing status enum values."""
        assert ProcessingStatus.PENDING.value == "PENDING"
        assert ProcessingStatus.PROCESSING.value == "PROCESSING"
        assert ProcessingStatus.COMPLETED.value == "COMPLETED"
        assert ProcessingStatus.FAILED_PROCESSING.value == "FAILED_PROCESSING"

    def test_extraction_method_values(self) -> None:
        """Test extraction method enum values."""
        assert ExtractionMethod.PYMUPDF.value == "PyMuPDF"
        assert ExtractionMethod.TESSERACT_OCR.value == "Tesseract_OCR"
