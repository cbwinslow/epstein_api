import logging
import sqlite3
from pathlib import Path
from typing import Any

from backend.core.interfaces import (
    DownloadStatus,
    DownloadTask,
    StateDBBase,
    StateDBProtocol,
)
from backend.core.settings import Settings
from backend.migrations.migrations import (
    MigrationVersion,
    get_all_migrations,
    get_migration_sql,
)

logger = logging.getLogger(__name__)


class SQLiteStateDB(StateDBBase):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._db_path = settings.database.sqlite_path
        self._conn: sqlite3.Connection | None = None
        self._ensure_db_dir()
        self._run_migrations()

    def _ensure_db_dir(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _run_migrations(self) -> None:
        conn = self._get_conn()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        applied = set(
            row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        )

        for version, sql in get_all_migrations():
            if version.value not in applied:
                logger.info(f"Running migration: {version.value}")
                conn.executescript(sql)
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version.value,))
                conn.commit()
                logger.info(f"Migration {version.value} completed")

    def save_task(self, task: DownloadTask) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO download_tasks 
            (url, dest_path, status, retries, error_message, sha256_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                task.url,
                str(task.dest_path),
                task.status.value,
                task.retries,
                task.error_message,
                task.sha256_hash,
            ),
        )
        conn.commit()
        logger.info(f"Saved task: {task.url} -> {task.status.value}")

    def get_task(self, url: str) -> DownloadTask | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM download_tasks WHERE url = ?", (url,)).fetchone()
        if row is None:
            return None
        return DownloadTask(
            url=row["url"],
            dest_path=Path(row["dest_path"]),
            status=DownloadStatus(row["status"]),
            retries=row["retries"],
            error_message=row["error_message"],
            sha256_hash=row["sha256_hash"],
        )

    def get_all_tasks(self) -> list[DownloadTask]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM download_tasks").fetchall()
        return [
            DownloadTask(
                url=row["url"],
                dest_path=Path(row["dest_path"]),
                status=DownloadStatus(row["status"]),
                retries=row["retries"],
                error_message=row["error_message"],
                sha256_hash=row["sha256_hash"],
            )
            for row in rows
        ]

    def update_status(self, url: str, status: DownloadStatus) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE download_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE url = ?",
            (status.value, url),
        )
        conn.commit()
        logger.info(f"Updated status for {url}: {status.value}")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
