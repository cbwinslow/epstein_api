"""
Unit tests for custom exceptions in core/exceptions.py.

These tests verify that exceptions log correctly and contain proper context.
"""

import pytest
from pathlib import Path

from backend.core.exceptions import (
    OSINTPipelineError,
    DownloadError,
    DownloadFailedError,
    DownloadTimeoutError,
    HashMismatchError,
    ProcessingError,
    OCRProcessingError,
    PDFProcessingError,
    FileTypeNotSupportedError,
    AgentError,
    AgentParsingError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    ConfigurationError,
    ValidationError,
    handle_error,
)


class TestOSINTPipelineError:
    """Tests for base OSINTPipelineError."""

    def test_basic_error(self) -> None:
        """Test creating a basic error."""
        error = OSINTPipelineError("Test error message")
        assert error.message == "Test error message"
        assert error.details == {}

    def test_error_with_details(self) -> None:
        """Test error with additional details."""
        error = OSINTPipelineError(
            "Test error",
            details={"url": "https://example.com", "status": 404},
        )
        assert error.details["url"] == "https://example.com"

    def test_error_with_original_exception(self) -> None:
        """Test wrapping original exception."""
        original = ValueError("Original error")
        error = OSINTPipelineError(
            "Wrapped error",
            original_exception=original,
        )
        assert error.original_exception is original

    def test_to_dict(self) -> None:
        """Test converting error to dictionary."""
        error = OSINTPipelineError(
            "Test",
            details={"key": "value"},
        )
        data = error.to_dict()
        assert data["message"] == "Test"
        assert data["details"]["key"] == "value"
        assert data["error_type"] == "OSINTPipelineError"


class TestDownloadErrors:
    """Tests for download-related errors."""

    def test_download_failed_error(self) -> None:
        """Test DownloadFailedError with full context."""
        error = DownloadFailedError(
            url="https://example.com/file.pdf",
            reason="Connection timeout",
            retries=3,
        )
        assert error.url == "https://example.com/file.pdf"
        assert error.reason == "Connection timeout"
        assert error.retries == 3

    def test_download_timeout_error(self) -> None:
        """Test DownloadTimeoutError."""
        error = DownloadTimeoutError(
            url="https://example.com/large.zip",
            timeout_seconds=300,
        )
        assert "timed out" in error.message.lower()

    def test_hash_mismatch_error(self) -> None:
        """Test HashMismatchError."""
        error = HashMismatchError(
            url="https://example.com/file.pdf",
            expected_hash="abc123",
            actual_hash="def456",
        )
        assert error.expected_hash == "abc123"
        assert error.actual_hash == "def456"


class TestProcessingErrors:
    """Tests for processing-related errors."""

    def test_ocr_processing_error(self) -> None:
        """Test OCRProcessingError with file path."""
        file_path = Path("/data/image001.png")
        error = OCRProcessingError(
            file_path=file_path,
            reason="Image too blurred for text recognition",
        )
        assert error.file_path == file_path
        assert "blurred" in error.reason

    def test_pdf_processing_error(self) -> None:
        """Test PDFProcessingError."""
        error = PDFProcessingError(
            file_path=Path("/data/doc.pdf"),
            reason="Encrypted PDF cannot be processed",
        )
        assert "Encrypted" in error.reason

    def test_file_type_not_supported_error(self) -> None:
        """Test FileTypeNotSupportedError."""
        error = FileTypeNotSupportedError(
            file_path=Path("/data/unknown.xyz"),
            supported_types=["pdf", "png", "jpg"],
        )
        assert "xyz" in error.message


class TestAgentErrors:
    """Tests for AI agent errors."""

    def test_agent_parsing_error(self) -> None:
        """Test AgentParsingError with validation errors."""
        raw_output = '{"invalid": "json"'
        validation_errors = ["Missing required field 'persons'", "Invalid date format"]

        error = AgentParsingError(
            agent_name="ExtractorAgent",
            raw_output=raw_output,
            validation_errors=validation_errors,
        )
        assert error.agent_name == "ExtractorAgent"
        assert len(error.validation_errors) == 2
        assert "persons" in error.validation_errors[0]


class TestDatabaseErrors:
    """Tests for database-related errors."""

    def test_database_connection_error(self) -> None:
        """Test DatabaseConnectionError."""
        error = DatabaseConnectionError(
            database_type="neo4j",
            connection_string="bolt://localhost:7687",
        )
        assert error.database_type == "neo4j"

    def test_database_query_error(self) -> None:
        """Test DatabaseQueryError."""
        error = DatabaseQueryError(
            query="MATCH (n) RETURN n",
            reason="Syntax error in Cypher query",
        )
        assert "Cypher" in error.reason


class TestHandleError:
    """Tests for error handling utility."""

    def test_wrap_osint_error(self) -> None:
        """Test that OSINT errors are returned as-is."""
        original = OSINTPipelineError("Original")
        wrapped = handle_error(original)
        assert wrapped is original

    def test_wrap_unknown_error(self) -> None:
        """Test wrapping unknown exceptions."""
        original = ValueError("Unknown error")
        wrapped = handle_error(original, context={"operation": "test"})
        assert isinstance(wrapped, OSINTPipelineError)
        assert wrapped.original_exception is original

    def test_wrap_runtime_error(self) -> None:
        """Test wrapping RuntimeError."""
        original = RuntimeError("Something went wrong")
        wrapped = handle_error(original, context={"step": "processing"})
        assert wrapped.details["step"] == "processing"
        assert wrapped.original_exception is original


class TestErrorHierarchy:
    """Tests for error class hierarchy."""

    def test_download_error_inherits(self) -> None:
        """Test that DownloadError inherits from OSINTPipelineError."""
        error = DownloadError("Test")
        assert isinstance(error, OSINTPipelineError)

    def test_processing_error_inherits(self) -> None:
        """Test that ProcessingError inherits from OSINTPipelineError."""
        error = ProcessingError("Test")
        assert isinstance(error, OSINTPipelineError)

    def test_agent_error_inherits(self) -> None:
        """Test that AgentError inherits from OSINTPipelineError."""
        error = AgentError("Test")
        assert isinstance(error, OSINTPipelineError)

    def test_database_error_inherits(self) -> None:
        """Test that DatabaseError inherits from OSINTPipelineError."""
        error = DatabaseError("Test")
        assert isinstance(error, OSINTPipelineError)
