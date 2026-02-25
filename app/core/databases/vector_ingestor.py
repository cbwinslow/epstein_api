"""
Vector ingestion pipeline.

Orchestrates text chunking, embedding, and ChromaDB ingestion.
"""

import logging
from pathlib import Path
from typing import Any

from backend.core.databases.chroma_client import ChromaDBClient
from backend.core.databases.chunker import TextChunker
from backend.core.exceptions import DatabaseQueryError
from backend.core.processing.sidecar import load_json_sidecar
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class VectorIngestor:
    """Pipeline for ingesting processed documents into vector DB."""

    def __init__(
        self,
        settings: Settings,
        chroma_client: ChromaDBClient | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        self._settings = settings
        self._chroma = chroma_client or ChromaDBClient(settings)
        self._chunker = chunker or TextChunker(settings)

    def ingest_sidecar(
        self,
        sidecar_path: Path,
        collection_name: str = "documents",
    ) -> dict[str, Any]:
        """Ingest a processed JSON sidecar into vector DB.

        Args:
            sidecar_path: Path to the JSON sidecar file.
            collection_name: ChromaDB collection name.

        Returns:
            Ingestion statistics.
        """
        try:
            doc = load_json_sidecar(sidecar_path)

            if not doc.raw_text or not doc.raw_text.strip():
                logger.warning(f"No text content in {sidecar_path}")
                return {"chunks": 0, "status": "skipped", "reason": "empty_text"}

            metadata = {
                "original_file_id": doc.original_file_id,
                "original_filename": doc.original_filename,
                "extraction_method": doc.extraction_method.value,
                "page_count": doc.page_count,
                "character_count": doc.character_count,
            }

            chunks = self._chunker.chunk_text(
                text=doc.raw_text,
                metadata=metadata,
            )

            if not chunks:
                return {"chunks": 0, "status": "skipped", "reason": "no_chunks"}

            documents = [chunk.text for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            ids = [f"doc_{doc.original_file_id}_chunk_{i}" for i in range(len(documents))]

            self._chroma.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(
                f"Ingested {len(chunks)} chunks from {doc.original_filename} "
                f"into collection {collection_name}"
            )

            return {
                "chunks": len(chunks),
                "status": "success",
                "file_id": doc.original_file_id,
                "filename": doc.original_filename,
            }

        except Exception as e:
            logger.error(f"Failed to ingest {sidecar_path}: {e}")
            raise DatabaseQueryError(
                query="ingest_sidecar",
                reason=str(e),
            ) from e

    def ingest_text(
        self,
        text: str,
        file_id: int,
        filename: str,
        collection_name: str = "documents",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest raw text into vector DB.

        Args:
            text: Raw text content.
            file_id: File identifier.
            filename: Original filename.
            collection_name: Collection name.
            metadata: Additional metadata.

        Returns:
            Ingestion statistics.
        """
        base_metadata = {
            "original_file_id": file_id,
            "original_filename": filename,
            **(metadata or {}),
        }

        chunks = self._chunker.chunk_text(text, base_metadata)

        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [f"doc_{file_id}_chunk_{i}" for i in range(len(documents))]

        self._chroma.add_documents(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

        return {
            "chunks": len(chunks),
            "status": "success",
            "file_id": file_id,
        }

    def query(
        self,
        query_text: str,
        collection_name: str = "documents",
        n_results: int = 10,
        file_id: int | None = None,
    ) -> dict[str, Any]:
        """Query the vector database.

        Args:
            query_text: Query text.
            collection_name: Collection to query.
            n_results: Number of results.
            file_id: Optional filter by file ID.

        Returns:
            Query results.
        """
        where = {"original_file_id": file_id} if file_id else None

        return self._chroma.query(
            collection_name=collection_name,
            query_text=query_text,
            n_results=n_results,
            where=where,
        )

    def close(self) -> None:
        """Close connections."""
        self._chroma.close()
