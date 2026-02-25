"""
MCP (Model Context Protocol) tools for agents.

Provides standardized access to:
- Read sidecar files
- Query vector database
- Search graph database
- Search system logs (AI feedback loop)
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from backend.core.databases.chroma_client import ChromaDBClient
from backend.core.databases.neo4j_client import Neo4jClient
from backend.core.processing.sidecar import load_json_sidecar, sidecar_exists
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class MCPTools:
    """MCP tools for agent access to data."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chroma = ChromaDBClient(settings)
        self._neo4j = Neo4jClient(settings)

    def read_sidecar(self, file_id: int, data_dir: str | None = None) -> dict[str, Any]:
        """Read a processed JSON sidecar file.

        Args:
            file_id: The file ID to read.
            data_dir: Optional data directory override.

        Returns:
            Sidecar data as dictionary.

        Raises:
            FileNotFoundError: If sidecar doesn't exist.
        """
        data_dir = data_dir or str(self._settings.storage.data_dir)

        search_path = Path(data_dir) / "processed"

        for sidecar_file in search_path.glob(f"*_{file_id}_processed.json"):
            return load_json_sidecar(sidecar_file).model_dump()

        for sidecar_file in search_path.glob("*.json"):
            try:
                data = load_json_sidecar(sidecar_file)
                if data.original_file_id == file_id:
                    return data.model_dump()
            except Exception:
                continue

        raise FileNotFoundError(f"No sidecar found for file_id: {file_id}")

    def read_sidecar_by_path(self, sidecar_path: Path) -> dict[str, Any]:
        """Read a specific sidecar by path.

        Args:
            sidecar_path: Path to sidecar file.

        Returns:
            Sidecar data.
        """
        if not sidecar_path.exists():
            raise FileNotFoundError(f"Sidecar not found: {sidecar_path}")

        return load_json_sidecar(sidecar_path).model_dump()

    def query_vector_db(
        self,
        query: str,
        collection: str = "documents",
        n_results: int = 10,
        file_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query the vector database for similar documents.

        Args:
            query: Search query text.
            collection: Collection name.
            n_results: Number of results.
            file_id: Optional filter by file ID.

        Returns:
            List of matching documents with metadata.
        """
        results = self._chroma.query(
            collection_name=collection,
            query_text=query,
            n_results=n_results,
        )

        output = []
        if results.get("documents"):
            for i, doc in enumerate(results["documents"]):
                output.append(
                    {
                        "text": doc,
                        "metadata": results.get("metadatas", [{}])[i],
                        "distance": results.get("distances", [0])[i],
                    }
                )

        return output

    def search_graph(
        self,
        entity_name: str | None = None,
        rel_type: str | None = None,
        cypher: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the knowledge graph.

        Args:
            entity_name: Find relationships for entity.
            rel_type: Filter by relationship type.
            cypher: Custom Cypher query (expert mode).

        Returns:
            Query results.
        """
        try:
            if cypher:
                return self._neo4j.execute_query(cypher)

            if entity_name:
                return self._neo4j.find_relationships(entity_name, rel_type)

            return []

        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return [{"error": str(e)}]

    def get_entity(self, name: str, label: str = "Person") -> dict[str, Any]:
        """Get a specific entity from the graph.

        Args:
            name: Entity name.
            label: Entity label (Person, Organization, etc.)

        Returns:
            Entity data.
        """
        if label == "Person":
            results = self._neo4j.find_person(name)
            return results[0] if results else {}

        return {}

    def close(self) -> None:
        """Close database connections."""
        self._chroma.close()
        self._neo4j.close()

    def search_system_logs(
        self,
        query: str,
        log_type: str = "all",
        limit: int = 20,
    ) -> str:
        """Search system logs for debugging and AI feedback.

        Args:
            query: Search query (e.g., file_id, ERROR, specific message).
            log_type: Which logs to search - "app", "ai_traces", or "all".
            limit: Maximum number of results to return.

        Returns:
            Formatted string summary of matching log entries.
        """
        base_dir = Path(self._settings.storage.data_dir).parent / "telemetry"
        app_dir = base_dir / "app"
        ai_traces_dir = base_dir / "ai_traces"

        results: list[dict[str, Any]] = []
        search_dirs: list[tuple[Path, str]] = []

        if log_type in ("all", "app"):
            search_dirs.append((app_dir, "app"))
        if log_type in ("all", "ai_traces"):
            search_dirs.append((ai_traces_dir, "ai_traces"))

        query_lower = query.lower()

        for log_dir, dir_name in search_dirs:
            if not log_dir.exists():
                continue

            for jsonl_file in log_dir.glob("*.jsonl"):
                try:
                    with open(jsonl_file, "r") as f:
                        for line in f:
                            if len(results) >= limit:
                                break
                            try:
                                entry = json.loads(line.strip())
                                entry_json = json.dumps(entry).lower()
                                if query_lower in entry_json:
                                    entry["_log_source"] = dir_name
                                    entry["_log_file"] = jsonl_file.name
                                    results.append(entry)
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning(f"Error reading {jsonl_file}: {e}")

        if not results:
            return f"No logs found matching query: '{query}'"

        output_lines = [
            f"Found {len(results)} log entries matching: '{query}'",
            "",
        ]

        for i, entry in enumerate(results[:limit], 1):
            timestamp = entry.get("timestamp", "unknown")
            level = entry.get("level", "INFO")
            source = entry.get("_log_source", "unknown")
            message = entry.get("message", "")

            output_lines.append(f"--- Entry {i} ---")
            output_lines.append(f"Time: {timestamp}")
            output_lines.append(f"Level: {level}")
            output_lines.append(f"Source: {source}")
            output_lines.append(f"Message: {message}")

            if "exception" in entry:
                output_lines.append(f"Exception: {entry['exception']}")

            if "token_usage" in entry:
                output_lines.append(f"Token Usage: {entry['token_usage']}")

            if "agent_name" in entry:
                output_lines.append(f"Agent: {entry['agent_name']}")

            if "metadata" in entry:
                output_lines.append(f"Metadata: {json.dumps(entry['metadata'], indent=2)}")

            output_lines.append("")

        return "\n".join(output_lines)
