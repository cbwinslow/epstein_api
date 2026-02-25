"""
Text chunking for RAG pipeline.

Provides semantic text splitting using RecursiveCharacterTextSplitter.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a text chunk with metadata."""

    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any]


class TextChunker:
    """Text chunker using RecursiveCharacterTextSplitter.

    Splits text into overlapping chunks for RAG ingestion.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.vectorization.chunk_size,
            chunk_overlap=settings.vectorization.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
            keep_separator=False,
        )

    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split text into chunks with metadata.

        Args:
            text: Input text to chunk.
            metadata: Metadata to attach to each chunk.

        Returns:
            List of TextChunk objects.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to chunker")
            return []

        texts = self._splitter.split_text(text)

        chunks = []
        start_char = 0

        for i, chunk_text in enumerate(texts):
            start_char = text.find(chunk_text, start_char)
            end_char = start_char + len(chunk_text)

            chunk_metadata = (metadata or {}).copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(texts)

            chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=i,
                    start_char=start_char,
                    end_char=end_char,
                    metadata=chunk_metadata,
                )
            )

            start_char = end_char

        logger.info(f"Split text into {len(chunks)} chunks")

        return chunks

    def chunk_documents(
        self,
        documents: list[tuple[str, dict[str, Any]]],
    ) -> list[tuple[str, dict[str, Any]]]:
        """Chunk multiple documents.

        Args:
            documents: List of (text, metadata) tuples.

        Returns:
            List of (chunk_text, chunk_metadata) tuples.
        """
        results = []

        for text, metadata in documents:
            chunks = self.chunk_text(text, metadata)
            for chunk in chunks:
                results.append((chunk.text, chunk.metadata))

        logger.info(f"Chunked {len(documents)} documents into {len(results)} chunks")

        return results

    @property
    def chunk_size(self) -> int:
        """Get chunk size."""
        return self._settings.vectorization.chunk_size

    @property
    def chunk_overlap(self) -> int:
        """Get chunk overlap."""
        return self._settings.vectorization.chunk_overlap
