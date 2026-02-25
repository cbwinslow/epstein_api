"""
File router with MIME type detection and fallback logic.

This module determines the appropriate extraction method based on file type
and content analysis.
"""

import logging
import mimetypes
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Supported file types for processing."""

    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    UNKNOWN = "unknown"


class ProcessingRoute(str, Enum):
    """Processing route determined by router."""

    NATIVE_PDF = "native_pdf"
    OCR_PDF = "ocr_pdf"
    OCR_IMAGE = "ocr_image"
    MEDIA_AUDIO = "media_audio"
    MEDIA_VIDEO = "media_video"
    UNSUPPORTED = "unsupported"


TEXT_DENSITY_THRESHOLD = 100


def detect_file_type(file_path: Path) -> FileType:
    """Detect the general file type based on MIME type.

    Args:
        file_path: Path to the file.

    Returns:
        FileType enum value.
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))

    if mime_type:
        if mime_type == "application/pdf":
            return FileType.PDF
        if mime_type.startswith("image/"):
            return FileType.IMAGE
        if mime_type.startswith("audio/"):
            return FileType.AUDIO
        if mime_type.startswith("video/"):
            return FileType.VIDEO

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return FileType.PDF
    if suffix in (".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"):
        return FileType.IMAGE
    if suffix in (".mp3", ".wav", ".ogg", ".flac", ".m4a"):
        return FileType.AUDIO
    if suffix in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        return FileType.VIDEO

    return FileType.UNKNOWN


def calculate_text_density(text: str, page_count: int) -> float:
    """Calculate average characters per page.

    Args:
        text: Extracted text.
        page_count: Number of pages in document.

    Returns:
        Average characters per page.
    """
    if page_count <= 0:
        return 0.0
    return len(text) / page_count


def should_use_ocr(text: str, page_count: int, force_ocr: bool = False) -> bool:
    """Determine if document should use OCR based on text density.

    Args:
        text: Extracted text from native PDF extraction.
        page_count: Number of pages.
        force_ocr: Force OCR regardless of density.

    Returns:
        True if OCR should be used.
    """
    if force_ocr:
        return True

    if page_count <= 0:
        return True

    density = calculate_text_density(text, page_count)
    is_scanned = density < TEXT_DENSITY_THRESHOLD

    if is_scanned:
        logger.info(
            f"Low text density detected ({density:.1f} chars/page). "
            f"Threshold: {TEXT_DENSITY_THRESHOLD}. Routing to OCR."
        )

    return is_scanned


def route_file(
    file_path: Path,
    initial_text: str | None = None,
    page_count: int | None = None,
    force_ocr: bool = False,
) -> ProcessingRoute:
    """Route a file to the appropriate processing pipeline.

    This is the main router function that determines how to process
    a file based on its type and content analysis.

    Args:
        file_path: Path to the file.
        initial_text: Optional text from initial extraction attempt.
        page_count: Number of pages in document.
        force_ocr: Force OCR regardless of analysis.

    Returns:
        ProcessingRoute enum value.

    Examples:
        >>> route_file(Path("document.pdf"))
        <ProcessingRoute.NATIVE_PDF: 'native_pdf'>

        >>> route_file(Path("scanned.pdf"), "", 10)
        <ProcessingRoute.OCR_PDF: 'ocr_pdf'>
    """
    file_type = detect_file_type(file_path)

    if file_type == FileType.PDF:
        return _route_pdf(file_path, initial_text, page_count, force_ocr)

    if file_type == FileType.IMAGE:
        return ProcessingRoute.OCR_IMAGE

    if file_type == FileType.AUDIO:
        return ProcessingRoute.MEDIA_AUDIO

    if file_type == FileType.VIDEO:
        return ProcessingRoute.MEDIA_VIDEO

    logger.warning(f"Unknown file type for: {file_path}")
    return ProcessingRoute.UNSUPPORTED


def _route_pdf(
    file_path: Path,
    initial_text: str | None,
    page_count: int | None,
    force_ocr: bool,
) -> ProcessingRoute:
    """Route a PDF file to native or OCR processing.

    Args:
        file_path: Path to PDF.
        initial_text: Text from native extraction.
        page_count: Number of pages.
        force_ocr: Force OCR flag.

    Returns:
        ProcessingRoute for PDF.
    """
    if force_ocr:
        logger.info(f"Forcing OCR for: {file_path}")
        return ProcessingRoute.OCR_PDF

    if initial_text is not None and page_count is not None:
        if should_use_ocr(initial_text, page_count, force_ocr):
            return ProcessingRoute.OCR_PDF
        return ProcessingRoute.NATIVE_PDF

    if initial_text is not None:
        if len(initial_text.strip()) < 100:
            return ProcessingRoute.OCR_PDF

    return ProcessingRoute.NATIVE_PDF


def get_supported_extensions() -> dict[FileType, list[str]]:
    """Get supported file extensions by type.

    Returns:
        Dictionary mapping FileType to list of extensions.
    """
    return {
        FileType.PDF: [".pdf"],
        FileType.IMAGE: [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"],
        FileType.AUDIO: [".mp3", ".wav", ".ogg", ".flac", ".m4a"],
        FileType.VIDEO: [".mp4", ".avi", ".mov", ".mkv", ".webm"],
    }


def is_supported(file_path: Path) -> bool:
    """Check if a file type is supported for processing.

    Args:
        file_path: Path to check.

    Returns:
        True if supported.
    """
    file_type = detect_file_type(file_path)
    return file_type != FileType.UNKNOWN
