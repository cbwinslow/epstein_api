"""
ChromaDB client for vector storage and semantic search.

Provides embedding generation using sentence-transformers and
vector storage with ChromaDB.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from backend.core.exceptions import DatabaseConnectionError, DatabaseQueryError
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """ChromaDB client with local embeddings.

    Uses sentence-transformers for local embedding generation.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: chromadb.PersistentClient | None = None
        self._embedding_model: SentenceTransformer | None = None

    def _get_client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self._settings.chromadb.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def _get_embedding_model(self) -> SentenceTransformer:
        """Get or create embedding model."""
        if self._embedding_model is None:
            model_name = self._settings.vectorization.model
            logger.info(f"Loading embedding model: {model_name}")
            self._embedding_model = SentenceTransformer(model_name)
        return self._embedding_model

    def get_collection(self, name: str) -> chromadb.Collection:
        """Get or create a collection."""
        return self._get_client().get_or_create_collection(name=name)

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Add documents with embeddings to collection.

        Args:
            collection_name: Name of the collection.
            documents: List of text documents.
            metadatas: List of metadata dicts.
            ids: Optional list of IDs.

        Raises:
            DatabaseQueryError: If embedding or insertion fails.
        """
        try:
            model = self._get_embedding_model()
            embeddings = model.encode(documents).tolist()

            collection = self.get_collection(collection_name)

            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]

            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"Added {len(documents)} documents to {collection_name}")

        except Exception as e:
            logger.error(f"Failed to add documents to {collection_name}: {e}")
            raise DatabaseQueryError(
                query="add_documents",
                reason=str(e),
            ) from e

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query collection with semantic search.

        Args:
            collection_name: Name of collection.
            query_text: Query text.
            n_results: Number of results.
            where: Optional metadata filter.

        Returns:
            Query results with documents, metadatas, distances.

        Raises:
            DatabaseQueryError: If query fails.
        """
        try:
            model = self._get_embedding_model()
            query_embedding = model.encode([query_text]).tolist()

            collection = self.get_collection(collection_name)

            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=where,
            )

            return results

        except Exception as e:
            logger.error(f"Query failed for {collection_name}: {e}")
            raise DatabaseQueryError(
                query="query",
                reason=str(e),
            ) from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        self._get_client().delete_collection(name=collection_name)
        logger.info(f"Deleted collection: {collection_name}")

    def reset(self) -> None:
        """Reset the database (delete all collections)."""
        self._get_client().reset()
        logger.warning("ChromaDB reset - all collections deleted")

    def close(self) -> None:
        """Close connections."""
        self._client = None
        self._embedding_model = None
