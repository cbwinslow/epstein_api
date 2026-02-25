"""
Unified Structured Logging with JSON Output

Provides enterprise-grade logging with:
- JSON formatter for structured logging
- Rotating file handlers to prevent disk overflow
- Automatic directory creation
- Global exception hooks
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["stack_trace"] = traceback.format_exception(*record.exc_info)

        if self.include_extra and hasattr(record, "metadata"):
            log_data["metadata"] = record.metadata

        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class TelemetryJSONFormatter(logging.Formatter):
    """JSON formatter for AI traces with token metrics."""

    def __init__(self):
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "type": getattr(record, "trace_type", "ai_trace"),
        }

        if hasattr(record, "prompt"):
            log_data["prompt"] = record.prompt
        if hasattr(record, "response"):
            log_data["response"] = record.response
        if hasattr(record, "model"):
            log_data["model"] = record.model
        if hasattr(record, "token_usage"):
            log_data["token_usage"] = record.token_usage
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name

        return json.dumps(log_data)


def get_telemetry_dir(base_dir: Path | None = None) -> dict[str, Path]:
    """Get or create telemetry directories."""
    if base_dir is None:
        base_dir = Path.cwd() / "data" / "telemetry"

    dirs = {
        "base": base_dir,
        "app": base_dir / "app",
        "ai_traces": base_dir / "ai_traces",
        "reports": base_dir / "reports",
        "tests": base_dir / "tests",
    }

    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    json_format: bool = True,
) -> logging.Logger:
    """Setup a logger with file and console handlers.

    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file name (appended to telemetry dir)
        max_bytes: Max file size before rotation
        backup_count: Number of backup files to keep
        json_format: Use JSON formatter

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    dirs = get_telemetry_dir()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    if json_format:
        console_handler.setFormatter(JSONFormatter(include_extra=True))
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    logger.addHandler(console_handler)

    if log_file:
        log_path = dirs["app"] / log_file
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter(include_extra=True))
        logger.addHandler(file_handler)

    return logger


def setup_ai_tracer(
    name: str = "ai_tracer",
    log_file: str = "trace.jsonl",
    level: int = logging.INFO,
) -> logging.Logger:
    """Setup AI tracer for LLM prompts and responses.

    Args:
        name: Logger name
        log_file: Output file in ai_traces dir
        level: Logging level

    Returns:
        Configured AI tracer
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    dirs = get_telemetry_dir()
    log_path = dirs["ai_traces"] / log_file

    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    handler.setLevel(level)
    handler.setFormatter(TelemetryJSONFormatter())
    logger.addHandler(handler)

    return logger


def log_ai_trace(
    logger: logging.Logger,
    agent_name: str,
    prompt: str,
    response: str,
    model: str,
    token_usage: dict[str, int],
) -> None:
    """Log an AI trace with metrics.

    Args:
        logger: AI tracer logger
        agent_name: Name of the agent
        prompt: Input prompt
        response: LLM response
        model: Model used
        token_usage: Dict with prompt_tokens, completion_tokens, total_tokens
    """
    extra = {
        "trace_type": "ai_trace",
        "agent_name": agent_name,
        "prompt": prompt,
        "response": response,
        "model": model,
        "token_usage": token_usage,
    }

    extra_record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="AI trace logged",
        args=(),
        exc_info=None,
    )
    extra_record.agent_name = agent_name
    extra_record.prompt = prompt
    extra_record.response = response
    extra_record.model = model
    extra_record.token_usage = token_usage
    extra_record.trace_type = "ai_trace"

    logger.handle(extra_record)


def setup_global_exception_hook(logger: logging.Logger) -> None:
    """Setup global exception hook to log uncaught exceptions.

    Args:
        logger: Logger to use for exception logging
    """

    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = exception_hook


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter for adding metadata to logs."""

    def process(self, msg, kwargs):
        return msg, {"extra": {"metadata": self.extra}}


def get_structured_logger(
    name: str,
    metadata: dict[str, Any] | None = None,
) -> LoggerAdapter:
    """Get a logger with structured metadata.

    Args:
        name: Logger name
        metadata: Optional metadata to include

    Returns:
        Logger adapter with metadata
    """
    logger = get_logger(name)
    if metadata:
        return LoggerAdapter(logger, metadata)
    return LoggerAdapter(logger, {})


def configure_root_logger(
    level: int = logging.INFO,
    json_format: bool = True,
) -> None:
    """Configure the root logger for the application.

    Args:
        level: Logging level
        json_format: Use JSON format
    """
    dirs = get_telemetry_dir()

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    if json_format:
        console_handler.setFormatter(JSONFormatter(include_extra=True))
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(console_handler)

    app_log = dirs["app"] / "app.log"
    file_handler = RotatingFileHandler(
        app_log,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(JSONFormatter(include_extra=True))
    root_logger.addHandler(file_handler)
