"""
Text extraction implementations for various file types.

Includes:
- PyMuPDF for native PDF text extraction
- pytesseract for OCR
- Placeholder for Whisper audio transcription
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

import fitz

from backend.core.exceptions import (
    AudioProcessingError,
    OCRProcessingError,
    PDFProcessingError,
)
from backend.core.processing.router import ProcessingRoute
from backend.core.processing.schemas import ExtractionMethod

logger = logging.getLogger(__name__)


class ExtractionResult:
    """Result of text extraction."""

    def __init__(
        self,
        text: str,
        method: ExtractionMethod,
        page_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.text = text
        self.method = method
        self.page_count = page_count
        self.metadata = metadata or {}


def extract_pdf_native(file_path: Path) -> ExtractionResult:
    """Extract text from PDF using PyMuPDF (fitz).

    Args:
        file_path: Path to PDF file.

    Returns:
        ExtractionResult with text and metadata.

    Raises:
        PDFProcessingError: If extraction fails.
    """
    try:
        doc = fitz.open(str(file_path))
        page_count = len(doc)

        text_parts = []
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text()
            text_parts.append(text)

        doc.close()

        full_text = "\n".join(text_parts)

        logger.info(
            f"Extracted {len(full_text)} characters from {page_count} pages "
            f"using PyMuPDF: {file_path.name}"
        )

        return ExtractionResult(
            text=full_text,
            method=ExtractionMethod.PYMUPDF,
            page_count=page_count,
            metadata={"extractor": "PyMuPDF"},
        )

    except Exception as e:
        logger.error(f"PyMuPDF extraction failed for {file_path}: {e}")
        raise PDFProcessingError(
            file_path=file_path,
            reason=str(e),
        ) from e


def extract_pdf_with_ocr(file_path: Path, language: str = "eng") -> ExtractionResult:
    """Extract text from PDF using OCR (pytesseract).

    Handles multi-page PDFs by converting pages to images first.

    Args:
        file_path: Path to PDF file.
        language: Tesseract language code (default: eng).

    Returns:
        ExtractionResult with OCR'd text.

    Raises:
        OCRProcessingError: If OCR fails.
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path

        logger.info(f"Starting OCR for PDF: {file_path.name}")

        images = convert_from_path(str(file_path))
        page_count = len(images)

        text_parts = []
        for page_num, image in enumerate(images):
            logger.debug(f"Processing page {page_num + 1}/{page_count}")
            text = pytesseract.image_to_string(image, lang=language)
            text_parts.append(text)

        full_text = "\n".join(text_parts)

        logger.info(
            f"OCR extracted {len(full_text)} characters from {page_count} pages: {file_path.name}"
        )

        return ExtractionResult(
            text=full_text,
            method=ExtractionMethod.TESSERACT_OCR,
            page_count=page_count,
            metadata={"extractor": "pytesseract", "language": language},
        )

    except Exception as e:
        logger.error(f"OCR extraction failed for {file_path}: {e}")
        raise OCRProcessingError(
            file_path=file_path,
            reason=str(e),
        ) from e


def extract_image_ocr(file_path: Path, language: str = "eng") -> ExtractionResult:
    """Extract text from image using OCR.

    Args:
        file_path: Path to image file.
        language: Tesseract language code.

    Returns:
        ExtractionResult with OCR'd text.

    Raises:
        OCRProcessingError: If OCR fails.
    """
    try:
        import pytesseract
        from PIL import Image

        logger.info(f"Starting OCR for image: {file_path.name}")

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang=language)

        logger.info(f"OCR extracted {len(text)} characters from image: {file_path.name}")

        return ExtractionResult(
            text=text,
            method=ExtractionMethod.TESSERACT_OCR,
            page_count=1,
            metadata={"extractor": "pytesseract", "language": language},
        )

    except Exception as e:
        logger.error(f"OCR extraction failed for {file_path}: {e}")
        raise OCRProcessingError(
            file_path=file_path,
            reason=str(e),
        ) from e


def extract_audio_transcription(file_path: Path) -> ExtractionResult:
    """Transcribe audio using Whisper.

    Placeholder implementation - requires whisper model setup.

    Args:
        file_path: Path to audio file.

    Returns:
        ExtractionResult with transcribed text.

    Raises:
        AudioProcessingError: If transcription fails.
    """
    logger.warning(f"Audio transcription not fully implemented: {file_path.name}")

    try:
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(str(file_path))

        return ExtractionResult(
            text=result["text"],
            method=ExtractionMethod.WHISPER_TRANSCRIPTION,
            metadata={"language": result.get("language")},
        )

    except Exception as e:
        logger.error(f"Audio transcription failed for {file_path}: {e}")
        raise AudioProcessingError(
            file_path=file_path,
            reason=str(e),
        ) from e


def extract_video_audio(file_path: Path) -> ExtractionResult:
    """Extract audio from video using ffmpeg, then transcribe.

    Placeholder implementation.

    Args:
        file_path: Path to video file.

    Returns:
        ExtractionResult with transcribed text.

    Raises:
        AudioProcessingError: If extraction fails.
    """
    logger.warning(f"Video audio extraction not fully implemented: {file_path.name}")

    audio_path = file_path.with_suffix(".audio.mp3")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(file_path),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-y",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
        )

        return extract_audio_transcription(audio_path)

    except subprocess.CalledProcessError as e:
        raise AudioProcessingError(
            file_path=file_path,
            reason=f"ffmpeg extraction failed: {e}",
        ) from e


def process_file(
    file_path: Path,
    route: ProcessingRoute,
    language: str = "eng",
) -> ExtractionResult:
    """Process a file based on the determined route.

    Args:
        file_path: Path to file.
        route: Processing route from router.
        language: Language for OCR.

    Returns:
        ExtractionResult with extracted text.
    """
    if route == ProcessingRoute.NATIVE_PDF:
        return extract_pdf_native(file_path)

    if route == ProcessingRoute.OCR_PDF:
        return extract_pdf_with_ocr(file_path, language)

    if route == ProcessingRoute.OCR_IMAGE:
        return extract_image_ocr(file_path, language)

    if route == ProcessingRoute.MEDIA_AUDIO:
        return extract_audio_transcription(file_path)

    if route == ProcessingRoute.MEDIA_VIDEO:
        return extract_video_audio(file_path)

    raise ValueError(f"Unsupported processing route: {route}")
