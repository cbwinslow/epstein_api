"""
Asynchronous download manager with state ledger.

This module provides async file downloading with:
- Concurrent download control via Semaphore
- Chunked downloading with HTTP Range support
- SHA-256 hash computation in chunks
- Exponential backoff retry logic
- SQLite state ledger with auto-resume
- WebSocket progress broadcasting
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

import aiohttp
import aiosqlite
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.exceptions import (
    DownloadFailedError,
    DownloadTimeoutError,
    HashMismatchError,
)
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


def sanitize_path(dest_path: Path, allowed_base: Path) -> Path:
    """Sanitize file path to prevent directory traversal attacks.

    Ensures the resolved path stays within the allowed base directory.
    Rejects paths containing '..' or absolute paths.

    Args:
        dest_path: The destination path to sanitize.
        allowed_base: The base directory that the path must be within.

    Returns:
        Sanitized Path object.

    Raises:
        ValueError: If the path would escape the allowed base directory.
    """
    # Resolve to absolute path and normalize
    resolved = (allowed_base / dest_path).resolve()

    # Check for directory traversal attempts
    if ".." in str(dest_path) or dest_path.is_absolute():
        raise ValueError(f"Path traversal attempt detected: {dest_path}")

    # Ensure final path is within allowed base
    try:
        resolved.relative_to(allowed_base)
    except ValueError:
        raise ValueError(f"Path {dest_path} escapes allowed directory {allowed_base}")

    return resolved


class DownloadStatus(str, Enum):
    """Download task status."""

    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


@dataclass
class DownloadTask:
    """Represents a download task in the ledger."""

    id: str | None = None
    source_url: str = ""
    local_filepath: str = ""
    status: DownloadStatus = DownloadStatus.PENDING
    bytes_downloaded: int = 0
    total_bytes: int | None = None
    sha256_hash: str | None = None
    retry_count: int = 0
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class DownloadProgress:
    """Progress update for WebSocket emission."""

    url: str
    bytes_downloaded: int
    total_bytes: int | None
    percentage: float
    status: DownloadStatus


class DownloadLedger:
    """Async SQLite ledger for tracking download tasks.

    Uses aiosqlite for async database operations.
    Automatically resumes incomplete downloads on startup.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the database and create tables."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS download_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT UNIQUE NOT NULL,
                    local_filepath TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    bytes_downloaded INTEGER DEFAULT 0,
                    total_bytes INTEGER,
                    sha256_hash TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON download_tasks(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash 
                ON download_tasks(sha256_hash)
            """)
            await db.commit()

        logger.info(f"Download ledger initialized at {self._db_path}")

    async def create_task(
        self,
        source_url: str,
        local_filepath: str,
    ) -> DownloadTask:
        """Create a new download task."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO download_tasks (source_url, local_filepath, status)
                VALUES (?, ?, ?)
                """,
                (source_url, local_filepath, DownloadStatus.PENDING.value),
            )
            await db.commit()
            task_id = cursor.lastrowid

        return DownloadTask(
            id=task_id,
            source_url=source_url,
            local_filepath=local_filepath,
            status=DownloadStatus.PENDING,
        )

    async def get_task_by_url(self, url: str) -> DownloadTask | None:
        """Get a task by URL."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiohttp.NamedTupleRow
            async with db.execute(
                "SELECT * FROM download_tasks WHERE source_url = ?",
                (url,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_task(row)
        return None

    async def get_task_by_hash(self, hash_value: str) -> DownloadTask | None:
        """Get a task by SHA-256 hash (for deduplication)."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiohttp.NamedTupleRow
            async with db.execute(
                "SELECT * FROM download_tasks WHERE sha256_hash = ? AND status = ?",
                (hash_value, DownloadStatus.COMPLETED.value),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_task(row)
        return None

    async def get_incomplete_tasks(self) -> list[DownloadTask]:
        """Get all incomplete tasks for resume on startup."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiohttp.NamedTupleRow
            async with db.execute(
                """
                SELECT * FROM download_tasks 
                WHERE status IN (?, ?)
                """,
                (DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]

    async def update_task(self, task: DownloadTask) -> None:
        """Update a task in the ledger."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE download_tasks SET
                    status = ?,
                    bytes_downloaded = ?,
                    total_bytes = ?,
                    sha256_hash = ?,
                    retry_count = ?,
                    error_message = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE source_url = ?
                """,
                (
                    task.status.value,
                    task.bytes_downloaded,
                    task.total_bytes,
                    task.sha256_hash,
                    task.retry_count,
                    task.error_message,
                    task.source_url,
                ),
            )
            await db.commit()

    async def get_all_tasks(self) -> list[DownloadTask]:
        """Get all tasks."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiohttp.NamedTupleRow
            async with db.execute("SELECT * FROM download_tasks") as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row: Any) -> DownloadTask:
        """Convert database row to DownloadTask."""
        return DownloadTask(
            id=row.id,
            source_url=row.source_url,
            local_filepath=row.local_filepath,
            status=DownloadStatus(row.status),
            bytes_downloaded=row.bytes_downloaded,
            total_bytes=row.total_bytes,
            sha256_hash=row.sha256_hash,
            retry_count=row.retry_count,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class AsyncDownloader:
    """Async file downloader with chunked downloads, retry logic, and progress tracking.

    Features:
    - aiohttp for async HTTP
    - asyncio.Semaphore for concurrency control
    - HTTP Range requests for resume
    - SHA-256 hash in chunks
    - Exponential backoff retry
    - WebSocket progress emission

    Args:
        settings: Application settings containing downloader configuration.
        progress_callback: Optional async callback for progress updates.
    """

    def __init__(
        self,
        settings: Settings,
        progress_callback: Callable[[DownloadProgress], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._progress_callback = progress_callback
        self._semaphore = asyncio.Semaphore(settings.downloader.max_concurrent)
        self._session: aiohttp.ClientSession | None = None
        self._ledger = DownloadLedger(settings.database.sqlite_path)
        self._active_downloads: dict[str, asyncio.Task] = {}

    async def initialize(self) -> None:
        """Initialize the downloader and resume incomplete downloads."""
        await self._ledger.initialize()

        incomplete = await self._ledger.get_incomplete_tasks()
        logger.info(f"Found {len(incomplete)} incomplete downloads to resume")

        for task in incomplete:
            await self.download(task.source_url, Path(task.local_filepath))

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self._settings.downloader.timeout,
                connect=30,
                sock_read=30,
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def download(
        self,
        url: str,
        dest_path: Path,
    ) -> DownloadTask:
        """Download a file from URL to destination.

        Uses semaphore for concurrency control and supports resume.

        Args:
            url: The URL to download from.
            dest_path: The destination path for the file.

        Returns:
            DownloadTask with final status.

        Raises:
            DownloadFailedError: If download fails after max retries.
        """
        async with self._semaphore:
            # Sanitize path to prevent directory traversal
            allowed_base = self._settings.storage.downloads_dir
            dest_path = sanitize_path(dest_path, allowed_base)

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            existing_task = await self._ledger.get_task_by_url(url)
            if existing_task:
                if existing_task.status == DownloadStatus.COMPLETED:
                    logger.info(f"Already downloaded: {url}")
                    return existing_task
                if existing_task.status == DownloadStatus.DUPLICATE:
                    logger.info(f"Duplicate file exists: {url}")
                    return existing_task

            task = existing_task or await self._ledger.create_task(
                source_url=url,
                local_filepath=str(dest_path),
            )

            task = await self._download_with_retry(task, dest_path)
            await self._ledger.update_task(task)

            return task

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        reraise=True,
    )
    async def _download_with_retry(
        self,
        task: DownloadTask,
        dest_path: Path,
    ) -> DownloadTask:
        """Download with retry logic using tenacity."""
        try:
            return await self._perform_download(task, dest_path)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            task.retry_count += 1
            task.error_message = str(e)
            if task.retry_count >= self._settings.downloader.max_retries:
                task.status = DownloadStatus.FAILED
                logger.error(f"Download failed after {task.retry_count} retries: {task.source_url}")
            else:
                logger.warning(
                    f"Retry {task.retry_count}/{self._settings.downloader.max_retries} for {task.source_url}"
                )
                raise
            return task

    async def _perform_download(
        self,
        task: DownloadTask,
        dest_path: Path,
    ) -> DownloadTask:
        """Perform the actual download with chunked reading and hashing."""
        task.status = DownloadStatus.DOWNLOADING
        await self._ledger.update_task(task)

        session = await self._get_session()
        headers = {}

        if dest_path.exists() and dest_path.stat().st_size > 0:
            existing_size = dest_path.stat().st_size
            task.bytes_downloaded = existing_size
            headers["Range"] = f"bytes={existing_size}-"
            logger.info(f"Resuming download from byte {existing_size}: {task.source_url}")

        sha256_hash = hashlib.sha256()
        downloaded = task.bytes_downloaded
        total_bytes: int | None = None

        try:
            async with session.get(task.source_url, headers=headers) as response:
                if response.status == 416:  # Range not satisfiable
                    dest_path.unlink()
                    downloaded = 0
                    task.bytes_downloaded = 0
                    async with session.get(task.source_url) as response:
                        total_bytes = int(response.headers.get("Content-Length", 0))
                        task.total_bytes = total_bytes
                        async for chunk in response.content.iter_chunked(
                            self._settings.downloader.chunk_size
                        ):
                            dest_path.open("wb").write(chunk)
                            sha256_hash.update(chunk)
                            downloaded += len(chunk)
                            task.bytes_downloaded = downloaded
                            await self._emit_progress(task, total_bytes)
                elif response.status in (200, 206):
                    total_bytes = int(response.headers.get("Content-Length", 0)) + downloaded
                    task.total_bytes = total_bytes

                    mode = "ab" if downloaded > 0 else "wb"
                    with dest_path.open(mode) as f:
                        async for chunk in response.content.iter_chunked(
                            self._settings.downloader.chunk_size
                        ):
                            f.write(chunk)
                            sha256_hash.update(chunk)
                            downloaded += len(chunk)
                            task.bytes_downloaded = downloaded
                            await self._emit_progress(task, total_bytes)
                else:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                    )

                final_hash = sha256_hash.hexdigest()

                existing_with_hash = await self._ledger.get_task_by_hash(final_hash)
                if existing_with_hash and existing_with_hash.source_url != task.source_url:
                    task.status = DownloadStatus.DUPLICATE
                    dest_path.unlink()
                    logger.info(f"Duplicate detected: {final_hash}")
                else:
                    task.sha256_hash = final_hash
                    task.status = DownloadStatus.COMPLETED
                    logger.info(f"Downloaded: {task.source_url} -> {dest_path} ({final_hash})")

        except asyncio.TimeoutError as e:
            task.status = DownloadStatus.FAILED
            task.error_message = "Timeout"
            raise DownloadTimeoutError(
                url=task.source_url,
                timeout_seconds=self._settings.downloader.timeout,
            ) from e
        except aiohttp.ClientError as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            raise DownloadFailedError(
                url=task.source_url,
                reason=str(e),
                retries=task.retry_count,
            ) from e

        await self._ledger.update_task(task)
        return task

    async def _emit_progress(
        self,
        task: DownloadTask,
        total_bytes: int,
    ) -> None:
        """Emit progress update if callback is configured."""
        if self._progress_callback and total_bytes > 0:
            percentage = (task.bytes_downloaded / total_bytes) * 100
            progress = DownloadProgress(
                url=task.source_url,
                bytes_downloaded=task.bytes_downloaded,
                total_bytes=total_bytes,
                percentage=percentage,
                status=task.status,
            )
            await self._progress_callback(progress)

    async def progress_stream(
        self,
        url: str,
    ) -> AsyncGenerator[DownloadProgress, None]:
        """Async generator for progress updates.

        Yields:
            DownloadProgress for each update.
        """
        session = await self._get_session()
        async with session.head(url) as response:
            total = int(response.headers.get("Content-Length", 0))

        downloaded = 0
        while downloaded < total:
            await asyncio.sleep(1)
            task = await self._ledger.get_task_by_url(url)
            if task:
                downloaded = task.bytes_downloaded
                yield DownloadProgress(
                    url=url,
                    bytes_downloaded=downloaded,
                    total_bytes=total,
                    percentage=(downloaded / total * 100) if total > 0 else 0,
                    status=task.status,
                )
            if task and task.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED):
                break

    async def pause(self, url: str) -> None:
        """Pause a download by URL."""
        task = await self._ledger.get_task_by_url(url)
        if task and task.status == DownloadStatus.DOWNLOADING:
            task.status = DownloadStatus.PAUSED
            await self._ledger.update_task(task)
            logger.info(f"Paused: {url}")

    async def cancel(self) -> None:
        """Cancel all active downloads."""
        for task in self._active_downloads.values():
            task.cancel()
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("All downloads cancelled")

    async def close(self) -> None:
        """Close the downloader and cleanup resources."""
        await self.cancel()
        logger.info("Downloader closed")
