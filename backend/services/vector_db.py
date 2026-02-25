import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.core.interfaces import VectorDBBase, VectorDBProtocol
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class ChromaDBClient(VectorDBBase):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = chromadb.PersistentClient(path=str(settings.chromadb.persist_directory))

    def add(
        self,
        collection: str,
        embeddings: list,
        documents: list,
        metadatas: list,
        ids: list[str] | None = None,
    ) -> None:
        coll = self._client.get_or_create_collection(name=collection)

        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        coll.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Added {len(documents)} documents to collection: {collection}")

    def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 10,
    ) -> dict[str, Any]:
        coll = self._client.get_or_create_collection(name=collection)

        results = coll.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        return results

    def delete_collection(self, collection: str) -> None:
        self._client.delete_collection(name=collection)
        logger.info(f"Deleted collection: {collection}")

    def get_collection(self, collection: str) -> Any:
        return self._client.get_or_create_collection(name=collection)

    def list_collections(self) -> list[str]:
        return [c.name for c in self._client.list_collections()]
