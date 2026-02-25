import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

import aiohttp

from backend.core.interfaces import (
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
    DownloaderProtocol,
)
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class AsyncDownloader(DownloaderBase):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session: aiohttp.ClientSession | None = None
        self._active_downloads: dict[str, asyncio.Task] = {}
        self._paused: set[str] = set()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._settings.downloader.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def download(self, url: str, dest_path: Path) -> DownloadTask:
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        task = DownloadTask(
            url=url,
            dest_path=dest_path,
            status=DownloadStatus.DOWNLOADING,
        )

        try:
            session = await self._get_session()
            headers = {}
            if dest_path.exists():
                existing_hash = await self._compute_file_hash(dest_path)
                if existing_hash:
                    task.sha256_hash = existing_hash
                    task.status = DownloadStatus.COMPLETED
                    return task
                headers["Range"] = f"bytes={dest_path.stat().st_size}-"

            async with session.get(url, headers=headers) as response:
                response.raise_for_status()

                content_length = response.headers.get("Content-Length")
                downloaded = dest_path.stat().st_size if dest_path.exists() else 0

                with open(dest_path, "ab" if headers else "wb") as f:
                    async for chunk in response.content.iter_chunked(
                        self._settings.downloader.chunk_size
                    ):
                        if url in self._paused:
                            await self.pause(url)
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

            task.sha256_hash = await self._compute_file_hash(dest_path)
            task.status = DownloadStatus.COMPLETED
            logger.info(f"Downloaded: {url} -> {dest_path}")

        except asyncio.CancelledError:
            task.status = DownloadStatus.PAUSED
            logger.warning(f"Download paused: {url}")
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            logger.error(f"Download failed: {url} - {e}")

        return task

    async def _compute_file_hash(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def pause(self, url: str) -> None:
        self._paused.add(url)
        if url in self._active_downloads:
            self._active_downloads[url].cancel()
            del self._active_downloads[url]

    async def resume(self, url: str) -> None:
        self._paused.discard(url)

    async def get_status(self, url: str) -> DownloadStatus | None:
        if url in self._paused:
            return DownloadStatus.PAUSED
        if url in self._active_downloads:
            return DownloadStatus.DOWNLOADING
        return DownloadStatus.PENDING

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
