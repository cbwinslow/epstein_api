#!/usr/bin/env python3
"""
Launch Logger - Logs all Docker launch activities to a file for debugging.

This script provides structured logging for the Epstein OSINT Pipeline launch process,
capturing all errors and results for later analysis.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

LOG_FILE = Path("/tmp/epstein_launch.log")


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def log(level: str, message: str, data: dict[str, Any] | None = None) -> None:
    """Log a message with timestamp and optional data."""
    entry = {
        "timestamp": get_timestamp(),
        "level": level,
        "message": message,
        "data": data or {},
    }
    
    # Also print to stdout for real-time feedback
    print(f"[{level}] {message}")
    if data:
        print(f"  Data: {json.dumps(data, indent=2)}")
    
    # Append to log file
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_error(message: str, error: Exception | None = None, **kwargs) -> None:
    """Log an error with exception details."""
    data = {"error_type": type(error).__name__ if error else None}
    if error:
        data["error_message"] = str(error)
    data.update(kwargs)
    log("ERROR", message, data)


def log_info(message: str, **kwargs) -> None:
    """Log an info message."""
    log("INFO", message, kwargs)


def log_success(message: str, **kwargs) -> None:
    """Log a success message."""
    log("SUCCESS", message, kwargs)


def log_warning(message: str, **kwargs) -> None:
    """Log a warning message."""
    log("WARNING", message, kwargs)


def read_logs() -> list[dict]:
    """Read all log entries from the log file."""
    entries = []
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
    return entries


def get_errors() -> list[dict]:
    """Get all error entries."""
    return [e for e in read_logs() if e.get("level") == "ERROR"]


def generate_report() -> str:
    """Generate a summary report of the launch."""
    entries = read_logs()
    errors = get_errors()
    
    report = []
    report.append("=" * 60)
    report.append("EPSTEIN OSINT PIPELINE - LAUNCH REPORT")
    report.append("=" * 60)
    report.append(f"Total log entries: {len(entries)}")
    report.append(f"Total errors: {len(errors)}")
    report.append("")
    
    if errors:
        report.append("ERRORS:")
        for error in errors:
            report.append(f"  - {error.get('message')}")
            if error_data := error.get("data", {}).get("error_message"):
                report.append(f"    {error_data}")
            report.append("")
    
    return "\n".join(report)


if __name__ == "__main__":
    # Test logging
    log_info("Logger initialized", log_file=str(LOG_FILE))
    print(f"\nLogging to: {LOG_FILE}")
    print(generate_report())
