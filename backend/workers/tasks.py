"""
Celery tasks for document processing.

This module contains the main processing task that orchestrates
file routing, extraction, and JSON sidecar creation.
"""

import logging
import time
from pathlib import Path

from backend.core.downloader import DownloadStatus
from backend.core.exceptions import (
    OCRProcessingError,
    PDFProcessingError,
    ProcessingError,
)
from backend.core.processing.extractors import (
    extract_image_ocr,
    extract_pdf_native,
    extract_pdf_with_ocr,
)
from backend.core.processing.router import (
    ProcessingRoute,
    is_supported,
    route_file,
)
from backend.core.processing.schemas import (
    ExtractionMethod,
    ProcessingResult,
    ProcessingStatus,
    ProcessedDocumentSchema,
)
from backend.core.processing.sidecar import save_json_sidecar
from backend.workers.celery_app import celery_app
from backend.workers.db import get_db_connection

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="epstein.process_document",
)
def process_document_task(self, file_id: int, force_ocr: bool = False) -> dict:
    """Process a document through the ETL pipeline.

    This is the main Celery task that:
    1. Retrieves file info from the ledger
    2. Routes to appropriate extractor
    3. Creates JSON sidecar
    4. Updates ledger status

    Args:
        file_id: ID of the file in the download ledger.
        force_ocr: Force OCR regardless of text density.

    Returns:
        Dictionary with processing result.
    """
    start_time = time.time()

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT source_url, local_filepath, status FROM download_tasks WHERE id = ?",
                (file_id,),
            )
            row = cursor.fetchone()

            if not row:
                logger.error(f"File not found in ledger: {file_id}")
                return {"error": "File not found", "file_id": file_id}

            source_url, local_filepath, status = row

            if status != DownloadStatus.COMPLETED.value:
                logger.warning(f"File not ready for processing: {file_id} (status: {status})")
                return {"error": "File not completed", "file_id": file_id}

        file_path = Path(local_filepath)

        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            _update_file_status(
                file_id, ProcessingStatus.FAILED_PROCESSING, "File not found on disk"
            )
            return {"error": "File not found", "file_id": file_id}

        if not is_supported(file_path):
            logger.error(f"Unsupported file type: {file_path}")
            _update_file_status(
                file_id, ProcessingStatus.FAILED_PROCESSING, "Unsupported file type"
            )
            return {"error": "Unsupported file type", "file_id": file_id}

        _update_file_status(file_id, ProcessingStatus.PROCESSING, None)

        extraction_result = _process_file(file_path, force_ocr)

        processed_doc = ProcessedDocumentSchema(
            original_file_id=file_id,
            original_filename=file_path.name,
            raw_text=extraction_result.text,
            extraction_method=extraction_result.method,
            page_count=extraction_result.page_count,
            character_count=len(extraction_result.text),
            word_count=len(extraction_result.text.split()),
        )

        sidecar_path = save_json_sidecar(file_path, processed_doc)

        _update_file_status(
            file_id,
            ProcessingStatus.COMPLETED,
            None,
            processing_method=extraction_result.method.value,
        )

        processing_time = time.time() - start_time

        logger.info(
            f"Processed file {file_id} ({file_path.name}) in {processing_time:.2f}s "
            f"using {extraction_result.method.value}"
        )

        return {
            "file_id": file_id,
            "status": "completed",
            "method": extraction_result.method.value,
            "sidecar_path": str(sidecar_path),
            "processing_time": processing_time,
        }

    except OCRProcessingError as e:
        logger.error(f"OCR processing failed for file {file_id}: {e}")
        _update_file_status(file_id, ProcessingStatus.FAILED_OCR, str(e))
        raise

    except PDFProcessingError as e:
        logger.error(f"PDF processing failed for file {file_id}: {e}")
        _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise

    except ProcessingError as e:
        logger.error(f"Processing failed for file {file_id}: {e}")
        _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise

    except Exception as e:
        logger.error(f"Unexpected error processing file {file_id}: {e}")
        _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise


def _process_file(file_path: Path, force_ocr: bool):
    """Process a file through extraction.

    Args:
        file_path: Path to file.
        force_ocr: Force OCR flag.

    Returns:
        ExtractionResult.
    """
    route = route_file(file_path, force_ocr=force_ocr)

    logger.info(f"Routing {file_path.name} to {route.value}")

    if route == ProcessingRoute.NATIVE_PDF:
        result = extract_pdf_native(file_path)

        if result.page_count and len(result.text.strip()) < 100:
            logger.info(f"Low text density, falling back to OCR for {file_path.name}")
            result = extract_pdf_with_ocr(file_path)

        return result

    if route == ProcessingRoute.OCR_PDF:
        return extract_pdf_with_ocr(file_path)

    if route == ProcessingRoute.OCR_IMAGE:
        return extract_image_ocr(file_path)

    if route in (ProcessingRoute.MEDIA_AUDIO, ProcessingRoute.MEDIA_VIDEO):
        raise NotImplementedError(f"Media processing not yet implemented: {route}")

    raise ValueError(f"Unsupported route: {route}")


def _update_file_status(
    file_id: int,
    status: ProcessingStatus,
    error_message: str | None = None,
    processing_method: str | None = None,
) -> None:
    """Update file status in the ledger.

    Args:
        file_id: ID of file.
        status: New status.
        error_message: Error message if failed.
        processing_method: Method used for processing.
    """
    with get_db_connection() as conn:
        if error_message:
            conn.execute(
                """
                UPDATE download_tasks 
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status.value, error_message, file_id),
            )
        elif processing_method:
            conn.execute(
                """
                UPDATE download_tasks 
                SET status = ?, processing_method = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status.value, processing_method, file_id),
            )
        else:
            conn.execute(
                """
                UPDATE download_tasks 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status.value, file_id),
            )
        conn.commit()
