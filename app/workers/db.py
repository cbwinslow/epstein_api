"""
Database connection helper for workers.

Provides context manager for SQLite database access.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from backend.core.settings import get_settings

settings = get_settings()


@contextmanager
def get_db_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection context manager.

    Args:
        db_path: Optional path to database. Defaults to settings.

    Yields:
        SQLite connection.
    """
    path = db_path or settings.database.sqlite_path
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
