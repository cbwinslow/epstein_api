"""
Router & ETL Fallback Tests

Tests for file type routing and OCR fallback logic.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND_PATH = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH.parent))


class TestFileRouter:
    """Test the file router for ETL pipeline."""

    def test_pdf_routes_to_pymupdf_for_text_extraction(self, temp_data_dir: Path):
        """Verify native PDF with high text density routes to PyMuPDF."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        # Create a mock PDF with high text density
        mock_pdf_path = temp_data_dir / "high_density.pdf"
        mock_pdf_path.write_bytes(b"%PDF-1.4 mock pdf with substantial text content")

        with patch("backend.core.processing.extractors.PDFExtractor") as mock_extractor:
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract.return_value = (
                "A" * 500
            )  # High text density
            mock_extractor.return_value = mock_extractor_instance

            result = router.route_file(str(mock_pdf_path))

            assert result["extractor"] == "pymupdf"
            mock_extractor_instance.extract.assert_called_once()

    def test_pdf_routes_to_ocr_for_scanned_documents(self, temp_data_dir: Path):
        """Verify scanned PDF with low text density triggers OCR fallback."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        # Create a mock scanned PDF (low text density)
        mock_pdf_path = temp_data_dir / "scanned_doc.pdf"
        mock_pdf_path.write_bytes(b"%PDF-1.4 mock scanned document")

        with patch("backend.core.processing.extractors.PDFExtractor") as mock_pdf:
            with patch("backend.core.processing.extractors.OCRExtractor") as mock_ocr:
                # PyMuPDF returns very little text (simulating scanned doc)
                mock_pdf_instance = MagicMock()
                mock_pdf_instance.extract.return_value = "X" * 50  # Low text density
                mock_pdf.return_value = mock_pdf_instance

                # OCR returns substantial text
                mock_ocr_instance = MagicMock()
                mock_ocr_instance.extract.return_value = "O" * 500
                mock_ocr.return_value = mock_ocr_instance

                result = router.route_file(str(mock_pdf_path))

                # Should fallback to OCR
                assert result["extractor"] == "ocr"
                mock_ocr_instance.extract.assert_called_once()

    def test_unsupported_file_raises_error(self, temp_data_dir: Path):
        """Verify unsupported file types raise FileTypeNotSupportedError."""
        from backend.core.processing.router import FileRouter
        from backend.core.exceptions import FileTypeNotSupportedError

        router = FileRouter()

        # Create unsupported file
        unsupported_file = temp_data_dir / "malware.exe"
        unsupported_file.write_bytes(b"MZ fake executable")

        with pytest.raises(FileTypeNotSupportedError) as exc_info:
            router.route_file(str(unsupported_file))

        assert "Unsupported file type" in str(exc_info.value)

    def test_unsupported_mime_type(self, temp_data_dir: Path):
        """Verify .zip files are handled correctly."""
        from backend.core.processing.router import FileRouter
        from backend.core.exceptions import FileTypeNotSupportedError

        router = FileRouter()

        zip_file = temp_data_dir / "archive.zip"
        zip_file.write_bytes(b"PK fake zip")

        with pytest.raises(FileTypeNotSupportedError):
            router.route_file(str(zip_file))


class TestMimeTypeDetection:
    """Test MIME type detection."""

    def test_pdf_mime_detection(self, temp_data_dir: Path):
        """Verify PDF MIME type is detected correctly."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        pdf_file = temp_data_dir / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mime_type = router._detect_mime_type(str(pdf_file))

        assert mime_type == "application/pdf"

    def test_png_mime_detection(self, temp_data_dir: Path):
        """Verify PNG MIME type is detected correctly."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        png_file = temp_data_dir / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mime_type = router._detect_mime_type(str(png_file))

        assert mime_type == "image/png"

    def test_jpeg_mime_detection(self, temp_data_dir: Path):
        """Verify JPEG MIME type is detected correctly."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        jpg_file = temp_data_dir / "test.jpg"
        jpg_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        mime_type = router._detect_mime_type(str(jpg_file))

        assert mime_type == "image/jpeg"

    def test_mp3_mime_detection(self, temp_data_dir: Path):
        """Verify MP3 MIME type is detected correctly."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        mp3_file = temp_data_dir / "test.mp3"
        mp3_file.write_bytes(b"ID3")  # MP3 starts with ID3

        mime_type = router._detect_mime_type(str(mp3_file))

        assert mime_type == "audio/mpeg"


class TestTextDensityCalculation:
    """Test text density calculation for OCR threshold."""

    def test_high_text_density_above_threshold(self):
        """Verify high text density is correctly identified."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        # 500 chars / 1 page = 500 chars/page (above 100 threshold)
        text = "A" * 500
        pages = 1

        density = router._calculate_text_density(text, pages)

        assert density == 500
        assert density > router.OCR_THRESHOLD

    def test_low_text_density_below_threshold(self):
        """Verify low text density triggers OCR."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        # 50 chars / 1 page = 50 chars/page (below 100 threshold)
        text = "X" * 50
        pages = 1

        density = router._calculate_text_density(text, pages)

        assert density == 50
        assert density < router.OCR_THRESHOLD

    def test_zero_text_density(self):
        """Verify empty text triggers OCR."""
        from backend.core.processing.router import FileRouter

        router = FileRouter()

        density = router._calculate_text_density("", 1)

        assert density == 0
        assert density < router.OCR_THRESHOLD


class TestExtractorInterface:
    """Test extractor interface compliance."""

    def test_pdf_extractor_interface(self):
        """Verify PDFExtractor has required interface."""
        from backend.core.processing.extractors import PDFExtractor

        extractor = PDFExtractor()

        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    def test_ocr_extractor_interface(self):
        """Verify OCRExtractor has required interface."""
        from backend.core.processing.extractors import OCRExtractor

        extractor = OCRExtractor()

        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    def test_audio_extractor_interface(self):
        """Verify AudioExtractor has required interface."""
        from backend.core.processing.extractors import AudioTranscriber

        transcriber = AudioTranscriber()

        assert hasattr(transcriber, "transcribe")
        assert callable(transcriber.transcribe)
