"""
FastAPI routes for document ingestion.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.interfaces import DownloadStatus
from backend.core.settings import get_settings
from backend.services.state_db import SQLiteStateDB
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_db_instance: SQLiteStateDB | None = None


def get_db() -> SQLiteStateDB:
    global _db_instance
    if _db_instance is None:
        settings = get_settings()
        _db_instance = SQLiteStateDB(settings)
    return _db_instance


class AddURLRequest(BaseModel):
    model_config = {"extra": "forbid"}
    url: str


class AddURLsRequest(BaseModel):
    model_config = {"extra": "forbid"}
    urls: list[str]


class TaskResponse(BaseModel):
    model_config = {"extra": "forbid"}
    url: str
    status: str
    dest_path: str | None = None
    error_message: str | None = None


@router.post("/url", response_model=TaskResponse)
async def add_url(request: AddURLRequest) -> TaskResponse:
    """Add a single URL to the download queue."""
    try:
        from backend.core.interfaces import DownloadTask
        from datetime import datetime

        db = get_db()

        settings = get_settings()
        url_hash = hash(request.url) % 10000000
        dest_path = settings.storage.downloads_dir / f"file_{url_hash}_{Path(request.url).name}"

        # Ensure we use absolute path for the worker
        abs_dest_path = str(dest_path.resolve())

        task = DownloadTask(
            url=request.url,
            dest_path=dest_path,
            status=DownloadStatus.PENDING,
            retries=0,
        )

        db.save_task(task)

        # Dispatch to Celery worker for download
        from app.workers.tasks import download_file_task
        celery_task = download_file_task.delay(request.url, abs_dest_path)
        
        logger.info(f"Added URL to queue: {request.url}, task_id={celery_task.id}")

        return TaskResponse(
            url=request.url,
            status=DownloadStatus.PENDING.value,
            dest_path=abs_dest_path,
        )

    except Exception as e:
        logger.error(f"Failed to add URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/urls", response_model=list[TaskResponse])
async def add_urls(request: AddURLsRequest) -> list[TaskResponse]:
    """Add multiple URLs to the download queue."""
    try:
        from backend.core.interfaces import DownloadTask

        db = get_db()
        settings = get_settings()
        results = []

        for url in request.urls:
            url_hash = hash(url) % 10000000
            dest_path = settings.storage.downloads_dir / f"file_{url_hash}_{Path(url).name}"

            task = DownloadTask(
                url=url,
                dest_path=dest_path,
                status=DownloadStatus.PENDING,
                retries=0,
            )

            db.save_task(task)

            results.append(
                TaskResponse(
                    url=url,
                    status=DownloadStatus.PENDING.value,
                    dest_path=str(dest_path),
                )
            )

        logger.info(f"Added {len(request.urls)} URLs to queue")

        return results

    except Exception as e:
        logger.error(f"Failed to add URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateStatusRequest(BaseModel):
    model_config = {"extra": "forbid"}
    url: str
    status: str


@router.post("/status")
async def update_task_status(request: UpdateStatusRequest) -> TaskResponse:
    """Update a task status (for testing/simulation)."""
    try:
        from urllib.parse import unquote
        from backend.core.interfaces import DownloadStatus

        url = unquote(request.url)
        db = get_db()

        try:
            new_status = DownloadStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

        db.update_status(url, new_status)

        task = db.get_task(url)

        return TaskResponse(
            url=task.url,
            status=task.status.value,
            dest_path=str(task.dest_path),
            error_message=task.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List download tasks."""
    try:
        db = get_db()
        tasks = db.get_all_tasks()

        if status:
            tasks = [t for t in tasks if t.status.value == status]

        return {
            "total": len(tasks),
            "tasks": [
                {
                    "url": t.url,
                    "status": t.status.value,
                    "dest_path": str(t.dest_path),
                    "retries": t.retries,
                    "error_message": t.error_message,
                }
                for t in tasks[:limit]
            ],
        }

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
