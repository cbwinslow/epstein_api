"""
Pytest configuration and shared fixtures.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# Add backend to path for imports
BACKEND_PATH = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH.parent))


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "downloads").mkdir()
    (data_dir / "processed").mkdir()
    return data_dir


@pytest.fixture
def mock_settings(temp_data_dir: Path) -> dict[str, Any]:
    """Mock settings for testing."""
    return {
        "app": {"name": "Test OSINT", "version": "0.1.0", "debug": True},
        "storage": {
            "data_dir": str(temp_data_dir),
            "downloads_dir": str(temp_data_dir / "downloads"),
            "processed_dir": str(temp_data_dir / "processed"),
        },
        "database": {"sqlite_path": str(temp_data_dir / "test.db")},
        "redis": {"host": "localhost", "port": 6379, "db": 0},
        "celery": {
            "broker_url": "redis://localhost:6379/0",
            "result_backend": "redis://localhost:6379/0",
        },
        "chromadb": {"persist_directory": str(temp_data_dir / "chromadb")},
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "test",
            "database": "neo4j",
        },
        "ollama": {"base_url": "http://localhost:11434", "model": "llama2"},
        "openrouter": {
            "api_key": "",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "google/gemma-2-9b-ite",
        },
        "downloader": {
            "max_concurrent": 5,
            "chunk_size": 8192,
            "timeout": 30,
            "max_retries": 3,
            "retry_backoff": 2.0,
        },
        "ocr": {"tesseract_path": None, "surya_enabled": True, "languages": ["eng"]},
        "vectorization": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "chunk_size": 512,
            "chunk_overlap": 50,
        },
        "websocket": {"host": "0.0.0.0", "port": 8001},
    }


@pytest.fixture
def sample_raw_text() -> str:
    """Sample raw text for entity extraction tests."""
    return """
    Jeffrey Epstein, a financier, flew on his private aircraft N228AW multiple times 
    with various passengers including Prince Andrew, Bill Clinton, and Donald Trump.
    The flights were documented between 2000 and 2019. Epstein's company, 
    Southern Trust Company, was registered in the US Virgin Islands.
    Meetings occurred at his New York mansion at 9 East 71st Street and 
    his private island Little St. James in the US Virgin Islands.
    """


@pytest.fixture
def sample_extracted_person() -> dict[str, Any]:
    """Sample extracted person data."""
    return {
        "full_name": "Jeffrey Epstein",
        "aliases": ["Jeff", "Eppy"],
        "titles": ["Mr."],
        "first_seen": "2000-01-01",
        "last_seen": "2019-07-01",
        "source_documents": ["flight_log_001.pdf"],
        "confidence": "high",
        "notes": "Financier, registered sex offender",
    }


@pytest.fixture
def sample_extracted_aircraft() -> dict[str, Any]:
    """Sample extracted aircraft data."""
    return {
        "tail_number": "N228AW",
        "make": "Boeing",
        "model": "737-7BC",
        "registration_country": "United States",
        "source_documents": ["flight_log_001.pdf"],
        "confidence": "high",
    }


@pytest.fixture
def sample_extracted_location() -> dict[str, Any]:
    """Sample extracted location data."""
    return {
        "name": "9 East 71st Street",
        "location_type": "residence",
        "address": "9 East 71st Street",
        "city": "New York",
        "state": "NY",
        "country": "United States",
        "source_documents": ["property_records.pdf"],
        "confidence": "high",
    }


@pytest.fixture
def sample_extracted_relationship() -> dict[str, Any]:
    """Sample extracted relationship data."""
    return {
        "from_entity": "Jeffrey Epstein",
        "to_entity": "Prince Andrew",
        "relationship_type": "FLEW_WITH",
        "score": 6,
        "evidence": ["Flight log shows both on N228AW on 2001-04-01"],
        "source_documents": ["flight_log_001.pdf"],
        "confidence": "medium",
    }


@pytest.fixture
def mock_neo4j_driver() -> MagicMock:
    """Mock Neo4j driver."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
    mock_session.run.return_value = []
    return mock_driver


@pytest.fixture
def mock_chroma_client() -> MagicMock:
    """Mock ChromaDB client."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_collection.query.return_value = {
        "documents": [],
        "metadatas": [],
        "distances": [],
    }
    return mock_client


@pytest.fixture
def mock_aiohttp_response() -> MagicMock:
    """Mock aiohttp response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Length": "1024"}
    mock_response.content.iter_chunked.return_value = iter([b"chunk1", b"chunk2"])
    mock_response.__aenter__ = MagicMock(return_value=mock_response)
    mock_response.__aexit__ = MagicMock(return_value=False)
    return mock_response


@pytest.fixture
def sample_download_task() -> dict[str, Any]:
    """Sample download task data."""
    return {
        "url": "https://example.com/document.pdf",
        "dest_path": "/tmp/downloads/document.pdf",
        "status": "PENDING",
        "retries": 0,
        "error_message": None,
        "sha256_hash": None,
    }


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis broker for Celery."""
    import fakeredis

    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    mocker.patch("redis.Redis", return_value=fake_redis)
    mocker.patch("celery.backends.redis.RedisBackend", return_value=fake_redis)
    return fake_redis


@pytest.fixture
def mock_neo4j_session(mocker):
    """Mock Neo4j session that captures Cypher queries."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

    captured_queries = []

    def capture_query(cypher, parameters=None):
        captured_queries.append({"cypher": cypher, "parameters": parameters})
        return []

    mock_session.run.side_effect = capture_query

    mocker.patch("neo4j.GraphDatabase.driver", return_value=mock_driver)

    return {
        "session": mock_session,
        "driver": mock_driver,
        "captured_queries": captured_queries,
    }


@pytest.fixture
def mock_openrouter_response():
    """Fixture that returns a structured JSON simulating LinkAnalyst scoring a Level 10 relationship."""

    def _mock_response(relationship_score: int = 10):
        import json

        mock_json = {
            "relationships": [
                {
                    "from_entity": "Jeffrey Epstein",
                    "to_entity": "Ghislaine Maxwell",
                    "relationship_type": "CO_CONSPIRATOR",
                    "score": relationship_score,
                    "evidence": [
                        "Both appeared on flight logs",
                        "Co-founded JEP Holdings together",
                        "Multiple witness testimonies confirm close professional relationship",
                    ],
                    "confidence": "high",
                },
                {
                    "from_entity": "Jeffrey Epstein",
                    "to_entity": "Prince Andrew",
                    "relationship_type": "FLEW_WITH",
                    "score": max(1, relationship_score - 2),
                    "evidence": [
                        "Flight log shows both on N977AJ on 2001-04-01",
                    ],
                    "confidence": "medium",
                },
            ]
        }
        return json.dumps(mock_json)

    return _mock_response


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama local LLM response."""

    def _mock_response(prompt: str) -> str:
        return '{"persons": [{"full_name": "Test Person", "aliases": [], "titles": [], "confidence": "high"}]}'

    return _mock_response
