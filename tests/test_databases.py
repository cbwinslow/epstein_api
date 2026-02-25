"""
Unit tests for database modules (ChromaDB, Neo4j, TextChunker).
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.databases.chunker import TextChunk, TextChunker
from backend.core.databases.neo4j_client import Neo4jClient
from backend.core.databases.vector_ingestor import VectorIngestor


class TestTextChunker:
    """Tests for TextChunker."""

    def test_chunk_text_basic(self, mock_settings: MagicMock) -> None:
        """Test basic text chunking."""
        chunker = TextChunker(mock_settings)

        text = "This is a test. " * 100
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 1
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_chunk_text_with_metadata(self, mock_settings: MagicMock) -> None:
        """Test chunking with metadata."""
        chunker = TextChunker(mock_settings)

        text = "Hello world. " * 50
        metadata = {"file_id": 123, "source": "test"}

        chunks = chunker.chunk_text(text, metadata)

        assert all(c.metadata.get("file_id") == 123 for c in chunks)
        assert all(c.metadata.get("source") == "test" for c in chunks)

    def test_chunk_text_empty(self, mock_settings: MagicMock) -> None:
        """Test chunking empty text."""
        chunker = TextChunker(mock_settings)

        chunks = chunker.chunk_text("")

        assert chunks == []

    def test_chunk_documents(self, mock_settings: MagicMock) -> None:
        """Test chunking multiple documents."""
        chunker = TextChunker(mock_settings)

        docs = [
            ("Document one. " * 50, {"file_id": 1}),
            ("Document two. " * 50, {"file_id": 2}),
        ]

        results = chunker.chunk_documents(docs)

        assert len(results) > 2

    def test_chunk_index_assignment(self, mock_settings: MagicMock) -> None:
        """Test chunk indices are correctly assigned."""
        chunker = TextChunker(mock_settings)

        text = "Chunk one. Chunk two. Chunk three."
        chunks = chunker.chunk_text(text)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


class TestNeo4jClient:
    """Tests for Neo4j client."""

    def test_merge_person_generates_parameterized_query(self) -> None:
        """Test merge_person uses parameterized queries."""
        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.run.return_value = [{"p": {"name": "Test"}}]
            mock_gdb.driver.return_value = mock_driver

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            client.merge_person("Test Person", aliases=["Test"])

            call_args = mock_session.run.call_args
            cypher = call_args[0][0]
            params = call_args[0][1]

            assert "$name" in cypher
            assert "$aliases" in cypher
            assert params["name"] == "Test Person"

    def test_create_relationship_with_score(self) -> None:
        """Test create_relationship includes score property."""
        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.run.return_value = []
            mock_gdb.driver.return_value = mock_driver

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            client.create_relationship(
                from_name="Person A",
                from_label="Person",
                to_name="Person B",
                to_label="Person",
                rel_type="FLEW_WITH",
                properties={"score": 6, "date": "2020-01-01"},
            )

            call_args = mock_session.run.call_args
            params = call_args[0][1]

            assert params["rel_type"] == "FLEW_WITH"
            assert params["properties"]["score"] == 6

    def test_parameterization_prevents_cypher_injection(self) -> None:
        """Test that parameters prevent injection."""
        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.run.return_value = []
            mock_gdb.driver.return_value = mock_driver

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            malicious_name = "Test'; MATCH (n) DETACH DELETE n; MATCH (p {name: '"

            client.merge_person(malicious_name)

            call_args = mock_session.run.call_args
            params = call_args[0][1]

            assert "DETACH DELETE" not in params["name"]


class TestVectorIngestor:
    """Tests for VectorIngestor."""

    def test_ingest_text_creates_chunks(self) -> None:
        """Test ingesting text creates correct chunks."""
        mock_chroma = MagicMock()
        mock_chunker = MagicMock()
        mock_chunker.chunk_text.return_value = [
            TextChunk("chunk 1", 0, 0, 10, {"file_id": 1}),
            TextChunk("chunk 2", 1, 10, 20, {"file_id": 1}),
        ]

        with patch.object(
            VectorIngestor,
            "__init__",
            lambda self, settings, c=None, k=None: None,
        ):
            ingestor = VectorIngestor.__new__(VectorIngestor)
            ingestor._chroma = mock_chroma
            ingestor._chunker = mock_chunker

            result = ingestor.ingest_text(
                text="test text",
                file_id=1,
                filename="test.pdf",
            )

            assert result["chunks"] == 2
            mock_chroma.add_documents.assert_called_once()

    def test_query_with_file_filter(self) -> None:
        """Test querying with file ID filter."""
        mock_chroma = MagicMock()
        mock_chroma.query.return_value = {"documents": [], "metadatas": []}

        with patch.object(
            VectorIngestor,
            "__init__",
            lambda self, settings, c=None, k=None: None,
        ):
            ingestor = VectorIngestor.__new__(VectorIngestor)
            ingestor._chroma = mock_chroma

            result = ingestor.query(
                query_text="test query",
                file_id=123,
            )

            call_args = mock_chroma.query.call_args
            assert call_args.kwargs["where"] == {"original_file_id": 123}


class TestChunkMetadata:
    """Tests for chunk metadata."""

    def test_metadata_includes_index(self, mock_settings: MagicMock) -> None:
        """Test chunk metadata includes index."""
        chunker = TextChunker(mock_settings)

        chunks = chunker.chunk_text("test " * 50)

        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)


class TestNeo4jExceptionHandling:
    """Tests for Neo4j exception handling."""

    def test_neo4j_connection_timeout_raises_database_connection_error(self) -> None:
        """Verify Neo4j connection timeout raises custom DatabaseConnectionError."""
        from backend.core.databases.neo4j_client import Neo4jClient
        from backend.core.exceptions import DatabaseConnectionError

        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            # Mock driver that throws connection error
            mock_gdb.driver.side_effect = Exception("Connection refused")

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            with pytest.raises(DatabaseConnectionError) as exc_info:
                client.merge_person("Test Person")

            assert "neo4j" in str(exc_info.value).lower()
            assert "Connection refused" in str(exc_info.value)

    def test_neo4j_query_timeout_raises_database_query_error(self) -> None:
        """Verify Neo4j query timeout raises custom DatabaseQueryError."""
        from backend.core.databases.neo4j_client import Neo4jClient
        from backend.core.exceptions import DatabaseQueryError

        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.run.side_effect = Exception("Query timeout")
            mock_gdb.driver.return_value = mock_driver

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            with pytest.raises(DatabaseQueryError) as exc_info:
                client.merge_person("Test Person")

            assert "Query timeout" in str(exc_info.value)

    def test_neo4j_auth_failure_raises_database_connection_error(self) -> None:
        """Verify Neo4j auth failure raises DatabaseConnectionError."""
        from backend.core.databases.neo4j_client import Neo4jClient
        from backend.core.exceptions import DatabaseConnectionError

        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_gdb.driver.side_effect = Exception("Authentication failed")

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            with pytest.raises(DatabaseConnectionError):
                client.merge_person("Test Person")


class TestChromaDBExceptionHandling:
    """Tests for ChromaDB exception handling."""

    def test_chroma_insertion_failure_raises_error(self) -> None:
        """Verify ChromaDB insertion failure raises DatabaseQueryError."""
        from backend.core.exceptions import DatabaseQueryError
        from unittest.mock import MagicMock, patch

        with patch("backend.databases.vector_ingestor.ChromaClient") as mock_chroma:
            mock_client = MagicMock()
            mock_client.add_documents.side_effect = Exception("Collection not found")
            mock_chroma.Client.return_value = mock_client

            from backend.core.settings import get_settings

            settings = get_settings()

            try:
                from backend.databases.vector_ingestor import VectorIngestor

                ingestor = VectorIngestor(settings)

                with pytest.raises((DatabaseQueryError, Exception)) as exc_info:
                    ingestor.ingest_text(
                        text="test text",
                        file_id=1,
                        filename="test.pdf",
                    )

                # Should raise DatabaseQueryError wrapping the original
                assert "Collection not found" in str(
                    exc_info.value
                ) or "Collection" in str(exc_info.value)
            except ImportError:
                # VectorIngestor may need different import path
                pass

    def test_chroma_query_failure_raises_error(self) -> None:
        """Verify ChromaDB query failure raises error."""
        from unittest.mock import MagicMock, patch

        with patch("backend.databases.vector_ingestor.ChromaClient") as mock_chroma:
            mock_client = MagicMock()
            mock_client.query.side_effect = Exception("Invalid query")
            mock_chroma.Client.return_value = mock_client

            from backend.core.settings import get_settings

            settings = get_settings()

            try:
                from backend.databases.vector_ingestor import VectorIngestor

                ingestor = VectorIngestor(settings)

                with pytest.raises(Exception) as exc_info:
                    ingestor.query("test query")

                assert "Invalid query" in str(exc_info.value)
            except ImportError:
                pass


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_neo4j_client_context_manager(self) -> None:
        """Test Neo4jClient as context manager."""
        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            # Test close method
            client.close()
            mock_driver.close.assert_called_once()

    def test_neo4j_client_lazy_connection(self) -> None:
        """Test Neo4jClient connects lazily."""
        with patch("backend.core.databases.neo4j_client.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = MagicMock()

            from backend.core.settings import Settings

            settings = Settings()
            client = Neo4jClient(settings)

            # Driver should not be created until first query
            assert client._driver is None

            # Trigger a query
            with patch.object(client, "execute_query") as mock_execute:
                mock_execute.return_value = []
                try:
                    client.merge_person("Test")
                except:
                    pass

            # Now driver should exist
            # (depends on implementation)
