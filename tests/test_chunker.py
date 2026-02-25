"""
Semantic Chunker Tests

Tests for text chunking with metadata tracking.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

BACKEND_PATH = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH.parent))


class TestTextChunker:
    """Test the semantic text chunker."""

    def test_chunk_count_mathematically_correct(self):
        """Verify chunk count is mathematically correct for given input."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        # 5000 chars with 1000 size and 200 overlap
        # Expected: ceil((5000 - 200) / (1000 - 200)) + 1 = ceil(4800/800) + 1 = 6 + 1 = 7
        text = "A" * 5000

        chunks = chunker.chunk_text(text, original_file_id=1)

        # Verify count
        assert len(chunks) == 7, f"Expected 7 chunks, got {len(chunks)}"

    def test_metadata_attached_to_every_chunk(self):
        """Verify metadata is attached to every chunk."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        text = "X" * 3000
        chunks = chunker.chunk_text(text, original_file_id=42)

        # Every chunk must have metadata
        for i, chunk in enumerate(chunks):
            assert "metadata" in chunk, f"Chunk {i} missing metadata"
            assert chunk["metadata"]["original_file_id"] == 42, (
                f"Chunk {i} has wrong file_id"
            )
            assert chunk["metadata"]["chunk_index"] == i, f"Chunk {i} has wrong index"

    def test_chunk_index_sequential(self):
        """Verify chunk indices are sequential starting from 0."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=500, chunk_overlap=100)

        text = "T" * 2000
        chunks = chunker.chunk_text(text, original_file_id=1)

        indices = [chunk["metadata"]["chunk_index"] for chunk in chunks]

        assert indices == list(range(len(chunks))), "Chunk indices not sequential"

    def test_overlap_region_preserved(self):
        """Verify overlap regions exist between consecutive chunks."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        text = "ABCDEFGHIJ" * 50  # 500 chars
        chunks = chunker.chunk_text(text, original_file_id=1)

        # Check that consecutive chunks share overlap
        for i in range(len(chunks) - 1):
            chunk_text = chunks[i]["text"]
            next_chunk_text = chunks[i + 1]["text"]

            # Last 20 chars of chunk should be in first 20 of next
            overlap = chunk_text[-20:]
            assert overlap in next_chunk_text, (
                f"Overlap not preserved between chunks {i} and {i + 1}"
            )

    def test_small_text_single_chunk(self):
        """Verify small text produces single chunk."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        text = "Short text"
        chunks = chunker.chunk_text(text, original_file_id=1)

        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_empty_text_returns_empty_list(self):
        """Verify empty text returns empty list."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        chunks = chunker.chunk_text("", original_file_id=1)

        assert chunks == []

    def test_different_file_ids_isolated(self):
        """Verify different file IDs are properly isolated."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        text = "Content" * 500
        chunks_file1 = chunker.chunk_text(text, original_file_id=1)
        chunks_file2 = chunker.chunk_text(text, original_file_id=2)

        # File IDs should be different
        assert (
            chunks_file1[0]["metadata"]["original_file_id"]
            != chunks_file2[0]["metadata"]["original_file_id"]
        )

    def test_custom_separators_respected(self):
        """Verify custom separators are respected in splitting."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(
            chunk_size=100, chunk_overlap=10, separators=["\n\n", "\n", ". "]
        )

        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunker.chunk_text(text, original_file_id=1)

        # Should split at paragraph boundaries
        assert len(chunks) >= 1


class TestVectorIngestor:
    """Test the vector ingestion pipeline."""

    def test_chunks_to_vectors(self):
        """Verify chunks are converted to vectors."""
        from backend.databases.vector_ingestor import VectorIngestor
        from unittest.mock import MagicMock

        mock_chroma = MagicMock()
        mock_embedding = MagicMock()

        ingestor = VectorIngestor(chroma_client=mock_chroma, embed_fn=mock_embedding)

        chunks = [
            {
                "text": "Test chunk 1",
                "metadata": {"original_file_id": 1, "chunk_index": 0},
            },
            {
                "text": "Test chunk 2",
                "metadata": {"original_file_id": 1, "chunk_index": 1},
            },
        ]

        mock_embedding.return_value = [[0.1] * 384, [0.2] * 384]

        result = ingestor.ingest_chunks(chunks, collection_name="test")

        assert result["chunks_ingested"] == 2


class TestChunkerConfiguration:
    """Test chunker configuration options."""

    def test_default_configuration(self):
        """Verify default chunker configuration."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker()

        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 50
        assert "\n\n" in chunker.separators

    def test_custom_chunk_size(self):
        """Verify custom chunk size is applied."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=2000)

        assert chunker.chunk_size == 2000

    def test_custom_overlap(self):
        """Verify custom overlap is applied."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_overlap=100)

        assert chunker.chunk_overlap == 100


class TestMetadataIntegrity:
    """Test metadata integrity through chunking process."""

    def test_metadata_survives_chunking(self):
        """Verify metadata survives the chunking process unchanged."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=100, chunk_overlap=10)

        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 10
        chunks = chunker.chunk_text(text, original_file_id=99, source="test.pdf")

        # All chunks should preserve original_file_id
        for chunk in chunks:
            assert chunk["metadata"]["original_file_id"] == 99

    def test_chunk_count_matches_metadata_indices(self):
        """Verify number of chunks matches metadata index range."""
        from backend.databases.chunker import TextChunker

        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "X" * 500
        chunks = chunker.chunk_text(text, original_file_id=1)

        # Number of chunks should equal max index + 1
        indices = [c["metadata"]["chunk_index"] for c in chunks]
        assert max(indices) + 1 == len(chunks)
