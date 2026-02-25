"""
Custom exception hierarchy for the OSINT Pipeline.

All exceptions automatically log errors with full traceback and context.
The system NEVER crashes from a single bad file - it logs, marks as FAILED, and continues.
"""

import logging
import traceback
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OSINTPipelineError(Exception):
    """Base exception for all OSINT Pipeline errors.

    All custom exceptions inherit from this base class to ensure consistent
    error handling across the entire application.

    Attributes:
        message: Human-readable error message.
        details: Additional context about the error (file, URL, etc.).
        original_exception: The original exception that was caught (if any).
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception

        super().__init__(self.message)
        self._log_error()

    def _log_error(self) -> None:
        """Log the error with full context."""
        log_data = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            **self.details,
        }

        if self.original_exception:
            log_data["original_error"] = str(self.original_exception)
            log_data["traceback"] = traceback.format_exc()

        logger.error(f"OSINT Pipeline Error: {log_data}")

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class DownloadError(OSINTPipelineError):
    """Base class for download-related errors."""

    pass


class DownloadFailedError(DownloadError):
    """Raised when a file download fails after all retries.

    This error is logged and the download task is marked as FAILED in the database.
    The system continues processing the next item in the queue.
    """

    def __init__(
        self,
        url: str,
        reason: str,
        retries: int = 0,
        original_exception: Exception | None = None,
    ) -> None:
        self.url = url
        self.reason = reason
        self.retries = retries
        super().__init__(
            message=f"Download failed for {url}: {reason}",
            details={
                "url": url,
                "reason": reason,
                "retries": retries,
            },
            original_exception=original_exception,
        )


class DownloadPausedError(DownloadError):
    """Raised when attempting to resume a paused download."""

    pass


class DownloadTimeoutError(DownloadError):
    """Raised when a download times out."""

    def __init__(
        self,
        url: str,
        timeout_seconds: int,
        original_exception: Exception | None = None,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        super().__init__(
            message=f"Download timed out for {url} after {timeout_seconds}s",
            details={"url": url, "timeout_seconds": timeout_seconds},
            original_exception=original_exception,
        )


class HashMismatchError(DownloadError):
    """Raised when file hash doesn't match expected hash.

    This indicates the file may be corrupted or tampered with.
    """

    def __init__(
        self,
        url: str,
        expected_hash: str,
        actual_hash: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.url = url
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            message=f"Hash mismatch for {url}: expected {expected_hash}, got {actual_hash}",
            details={
                "url": url,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
            },
            original_exception=original_exception,
        )


class ProcessingError(OSINTPipelineError):
    """Base class for file processing errors."""

    pass


class OCRProcessingError(ProcessingError):
    """Raised when OCR processing fails.

    The system logs the failure, marks the file as FAILED, and continues.
    """

    def __init__(
        self,
        file_path: Path,
        reason: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(
            message=f"OCR failed for {file_path}: {reason}",
            details={"file_path": str(file_path), "reason": reason},
            original_exception=original_exception,
        )


class PDFProcessingError(ProcessingError):
    """Raised when PDF processing fails."""

    def __init__(
        self,
        file_path: Path,
        reason: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(
            message=f"PDF processing failed for {file_path}: {reason}",
            details={"file_path": str(file_path), "reason": reason},
            original_exception=original_exception,
        )


class AudioProcessingError(ProcessingError):
    """Raised when audio transcription fails."""

    pass


class FileTypeNotSupportedError(ProcessingError):
    """Raised when a file type is not supported for processing."""

    def __init__(
        self,
        file_path: Path,
        supported_types: list[str],
        original_exception: Exception | None = None,
    ) -> None:
        self.file_path = file_path
        self.supported_types = supported_types
        super().__init__(
            message=f"File type not supported for {file_path}. Supported: {supported_types}",
            details={"file_path": str(file_path), "supported_types": supported_types},
            original_exception=original_exception,
        )


class AgentError(OSINTPipelineError):
    """Base class for AI agent errors."""

    pass


class AgentParsingError(AgentError):
    """Raised when AI agent fails to parse or extract data.

    This ensures the AI returns valid structured data before reaching databases.
    """

    def __init__(
        self,
        agent_name: str,
        raw_output: str,
        validation_errors: list[str],
        original_exception: Exception | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.raw_output = raw_output
        self.validation_errors = validation_errors
        super().__init__(
            message=f"{agent_name} failed to produce valid output",
            details={
                "agent_name": agent_name,
                "raw_output": raw_output[:500],
                "validation_errors": validation_errors,
            },
            original_exception=original_exception,
        )


class AgentRateLimitError(AgentError):
    """Raised when AI API rate limit is exceeded."""

    pass


class AgentConfigurationError(AgentError):
    """Raised when AI agent is misconfigured."""

    pass


class DatabaseError(OSINTPipelineError):
    """Base class for database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails.

    The system attempts reconnection before raising this error.
    """

    def __init__(
        self,
        database_type: str,
        connection_string: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.database_type = database_type
        self.connection_string = connection_string
        super().__init__(
            message=f"Failed to connect to {database_type} database",
            details={"database_type": database_type, "connection_string": connection_string},
            original_exception=original_exception,
        )


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""

    def __init__(
        self,
        query: str,
        reason: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.query = query
        self.reason = reason
        super().__init__(
            message=f"Database query failed: {reason}",
            details={"query": query, "reason": reason},
            original_exception=original_exception,
        )


class EntityValidationError(DatabaseError):
    """Raised when entity data fails validation before database insertion.

    This prevents invalid data from reaching Neo4j/ChromaDB.
    """

    pass


class MigrationError(DatabaseError):
    """Raised when database migration fails."""

    pass


class ConfigurationError(OSINTPipelineError):
    """Raised when configuration is invalid or missing."""

    pass


class ValidationError(OSINTPipelineError):
    """Raised when input validation fails."""

    pass


class WebSocketError(OSINTPipelineError):
    """Base class for WebSocket errors."""

    pass


class WebSocketConnectionError(WebSocketError):
    """Raised when WebSocket connection fails."""

    pass


class QueueError(OSINTPipelineError):
    """Base class for queue-related errors."""

    pass


class QueueConnectionError(QueueError):
    """Raised when queue connection fails."""

    pass


class TaskNotFoundError(QueueError):
    """Raised when a queued task is not found."""

    pass


def handle_error(
    error: Exception,
    context: dict[str, Any] | None = None,
) -> OSINTPipelineError:
    """Convert any exception to OSINTPipelineError with context.

    This function wraps unknown exceptions into the OSINT pipeline error
    hierarchy, ensuring consistent error handling.

    Args:
        error: The original exception to wrap.
        context: Additional context about where the error occurred.

    Returns:
        OSINTPipelineError with full context.
    """
    context = context or {}

    if isinstance(error, OSINTPipelineError):
        return error

    return OSINTPipelineError(
        message=str(error),
        details=context,
        original_exception=error,
    )
