"""
Telemetry and audit logging for agent decisions.

Logs all agent decisions to:
- SQLite for audit trail
- JSON files for structured logging
- AI traces for LLM metrics
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.core.settings import Settings
from backend.core.logger import setup_ai_tracer, log_ai_trace, get_telemetry_dir

logger = logging.getLogger(__name__)

_ai_tracer: logging.Logger | None = None


def get_ai_tracer() -> logging.Logger:
    """Get or create the AI tracer logger."""
    global _ai_tracer
    if _ai_tracer is None:
        _ai_tracer = setup_ai_tracer()
    return _ai_tracer


class TelemetryLogger:
    """Logs agent decisions to SQLite audit trail and JSON files."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._db_path = settings.database.sqlite_path.parent / "audit_trail.db"
        self._ensure_db()
        self._ai_tracer = get_ai_tracer()

    def _ensure_db(self) -> None:
        """Ensure audit database exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                input_file TEXT,
                logic_reasoning TEXT,
                output_data TEXT,
                confidence_score REAL,
                status TEXT,
                error_message TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_audit_timestamp 
            ON agent_audit(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_audit_agent 
            ON agent_audit(agent_name)
        """)
        conn.commit()
        conn.close()

    def log(
        self,
        agent_name: str,
        input_file: str | None = None,
        logic_reasoning: str | None = None,
        output_data: dict[str, Any] | None = None,
        confidence_score: float | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        """Log an agent decision to SQLite and JSON.

        Args:
            agent_name: Name of the agent.
            input_file: File being processed.
            logic_reasoning: Agent's reasoning.
            output_data: Output from agent.
            confidence_score: Confidence (0-1).
            status: success/error.
            error_message: Error if any.
        """
        conn = sqlite3.connect(str(self._db_path))

        conn.execute(
            """
            INSERT INTO agent_audit 
            (timestamp, agent_name, input_file, logic_reasoning, output_data, confidence_score, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                agent_name,
                input_file,
                logic_reasoning,
                json.dumps(output_data) if output_data else None,
                confidence_score,
                status,
                error_message,
            ),
        )

        conn.commit()
        conn.close()

        logger.debug(f"Logged {agent_name} decision: {status}")

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": agent_name,
            "input_file": input_file,
            "logic_reasoning": logic_reasoning,
            "output_data": output_data,
            "confidence_score": confidence_score,
            "status": status,
            "error_message": error_message,
        }

        dirs = get_telemetry_dir()
        log_file = dirs["app"] / "agent_audit.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def log_ai_call(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        model: str,
        token_usage: dict[str, int],
    ) -> None:
        """Log an LLM call with metrics.

        Args:
            agent_name: Name of the agent
            prompt: Input prompt
            response: LLM response
            model: Model used
            token_usage: Dict with prompt_tokens, completion_tokens, total_tokens
        """
        log_ai_trace(
            self._ai_tracer,
            agent_name=agent_name,
            prompt=prompt,
            response=response,
            model=model,
            token_usage=token_usage,
        )

    def get_logs(
        self,
        agent_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve audit logs.

        Args:
            agent_name: Filter by agent.
            limit: Max results.

        Returns:
            List of log entries.
        """
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row

        if agent_name:
            cursor = conn.execute(
                "SELECT * FROM agent_audit WHERE agent_name = ? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM agent_audit ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_failed_operations(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get failed operations for debugging.

        Args:
            limit: Max results.

        Returns:
            List of failed operations.
        """
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            "SELECT * FROM agent_audit WHERE status = 'error' ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]


class QuarantineManager:
    """Manages files that failed agent processing.

    Moves problematic files to quarantine for human review.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._quarantine_dir = settings.storage.data_dir / "quarantine"
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)

    def quarantine_file(
        self,
        file_path: Path,
        reason: str,
        agent_name: str | None = None,
        error_details: str | None = None,
    ) -> Path:
        """Move a file to quarantine.

        Args:
            file_path: Path to file to quarantine.
            reason: Reason for quarantine.
            agent_name: Agent that processed the file.
            error_details: Detailed error information.

        Returns:
            Path to quarantined file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_name = f"{timestamp}_{file_path.name}"
        quarantine_path = self._quarantine_dir / quarantine_name

        import shutil

        shutil.copy2(file_path, quarantine_path)

        metadata = {
            "original_path": str(file_path),
            "quarantine_time": datetime.now().isoformat(),
            "reason": reason,
            "agent": agent_name,
            "error_details": error_details,
        }

        meta_path = quarantine_path.with_suffix(".meta.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Quarantined {file_path.name}: {reason}")

        return quarantine_path

    def list_quarantine(self) -> list[dict[str, Any]]:
        """List all quarantined files.

        Returns:
            List of quarantine entries with metadata.
        """
        entries = []

        for meta_file in self._quarantine_dir.glob("*.meta.json"):
            with open(meta_file) as f:
                metadata = json.load(f)

            entry = {
                "filename": meta_file.stem.replace("_", " ", 1),
                "quarantine_path": str(meta_file.parent / meta_file.stem),
                "quarantine_time": metadata.get("quarantine_time"),
                "reason": metadata.get("reason"),
                "agent": metadata.get("agent"),
            }
            entries.append(entry)

        entries.sort(key=lambda x: x["quarantine_time"] or "", reverse=True)

        return entries

    def release_file(self, quarantine_path: Path, destination: Path) -> None:
        """Release a file from quarantine.

        Args:
            quarantine_path: Path to quarantined file.
            destination: Destination path.
        """
        import shutil

        shutil.copy2(quarantine_path, destination)

        meta_path = quarantine_path.with_suffix(".meta.json")
        if meta_path.exists():
            meta_path.unlink()

        quarantine_path.unlink()

        logger.info(f"Released {quarantine_path.name} to {destination}")
