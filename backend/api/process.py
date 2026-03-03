"""
FastAPI routes for document processing.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.settings import get_settings
from backend.services.state_db import SQLiteStateDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/process", tags=["process"])

_db_instance: SQLiteStateDB | None = None


def get_db() -> SQLiteStateDB:
    global _db_instance
    if _db_instance is None:
        settings = get_settings()
        _db_instance = SQLiteStateDB(settings)
    return _db_instance


class ProcessRequest(BaseModel):
    model_config = {"extra": "forbid"}
    url: str
    force_ocr: bool = False


class ProcessResponse(BaseModel):
    model_config = {"extra": "forbid"}
    task_id: str | None = None
    status: str
    message: str


@router.post("/document", response_model=ProcessResponse)
async def process_document(request: ProcessRequest) -> ProcessResponse:
    """Trigger document processing via Celery."""
    try:
        from backend.workers.tasks import process_document_task

        db = get_db()
        task = db.get_task(request.url)

        if not task:
            raise HTTPException(status_code=404, detail="URL not found in queue")

        if task.status.value != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"File not ready for processing (status: {task.status.value})",
            )

        celery_task = process_document_task.delay(request.url, request.force_ocr)

        logger.info(f"Queued processing task for url={request.url}, task_id={celery_task.id}")

        return ProcessResponse(
            task_id=celery_task.id,
            status="queued",
            message=f"Processing task queued for {request.url}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{url}")
async def get_processing_status(url: str) -> dict[str, Any]:
    """Get the processing status of a file."""
    try:
        from urllib.parse import unquote

        url = unquote(url)

        db = get_db()
        task = db.get_task(url)

        if not task:
            raise HTTPException(status_code=404, detail="URL not found")

        return {
            "url": task.url,
            "status": task.status.value,
            "dest_path": str(task.dest_path),
            "processing_method": task.processing_method,
            "error_message": task.error_message,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_processing_stats() -> dict[str, int]:
    """Get processing statistics."""
    try:
        db = get_db()
        tasks = db.get_all_tasks()

        stats = {
            "total": len(tasks),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
        }

        for task in tasks:
            status = task.status.value
            if status == "PENDING":
                stats["pending"] += 1
            elif status == "PROCESSING":
                stats["processing"] += 1
            elif status == "COMPLETED":
                stats["completed"] += 1
            elif "FAILED" in status:
                stats["failed"] += 1

        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
