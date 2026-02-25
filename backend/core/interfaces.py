from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


class DownloadStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class DownloadTask:
    url: str
    dest_path: Path
    status: DownloadStatus
    retries: int = 0
    error_message: str | None = None
    sha256_hash: str | None = None


@runtime_checkable
class DownloaderProtocol(Protocol):
    async def download(self, url: str, dest_path: Path) -> DownloadTask: ...
    async def pause(self, url: str) -> None: ...
    async def resume(self, url: str) -> None: ...
    async def get_status(self, url: str) -> DownloadStatus | None: ...


class DownloaderBase(ABC):
    @abstractmethod
    async def download(self, url: str, dest_path: Path) -> DownloadTask:
        pass

    @abstractmethod
    async def pause(self, url: str) -> None:
        pass

    @abstractmethod
    async def resume(self, url: str) -> None:
        pass

    @abstractmethod
    async def get_status(self, url: str) -> DownloadStatus | None:
        pass


@runtime_checkable
class ProcessorProtocol(Protocol):
    def can_process(self, file_path: Path) -> bool: ...
    async def process(self, file_path: Path) -> dict: ...


class ProcessorBase(ABC):
    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    async def process(self, file_path: Path) -> dict:
        pass


@runtime_checkable
class VectorDBProtocol(Protocol):
    def add(self, collection: str, embeddings: list, documents: list, metadatas: list) -> None: ...
    def query(self, collection: str, query_text: str, n_results: int) -> list: ...
    def delete_collection(self, collection: str) -> None: ...


class VectorDBBase(ABC):
    @abstractmethod
    def add(self, collection: str, embeddings: list, documents: list, metadatas: list) -> None:
        pass

    @abstractmethod
    def query(self, collection: str, query_text: str, n_results: int) -> list:
        pass

    @abstractmethod
    def delete_collection(self, collection: str) -> None:
        pass


@runtime_checkable
class GraphDBProtocol(Protocol):
    def execute_query(self, cypher: str) -> list: ...
    def create_node(self, label: str, properties: dict) -> None: ...
    def create_relationship(
        self, from_node: str, to_node: str, rel_type: str, properties: dict
    ) -> None: ...


class GraphDBBase(ABC):
    @abstractmethod
    def execute_query(self, cypher: str) -> list:
        pass

    @abstractmethod
    def create_node(self, label: str, properties: dict) -> None:
        pass

    @abstractmethod
    def create_relationship(
        self, from_node: str, to_node: str, rel_type: str, properties: dict
    ) -> None:
        pass


@runtime_checkable
class StateDBProtocol(Protocol):
    def save_task(self, task: DownloadTask) -> None: ...
    def get_task(self, url: str) -> DownloadTask | None: ...
    def get_all_tasks(self) -> list[DownloadTask]: ...
    def update_status(self, url: str, status: DownloadStatus) -> None: ...


class StateDBBase(ABC):
    @abstractmethod
    def save_task(self, task: DownloadTask) -> None:
        pass

    @abstractmethod
    def get_task(self, url: str) -> DownloadTask | None:
        pass

    @abstractmethod
    def get_all_tasks(self) -> list[DownloadTask]:
        pass

    @abstractmethod
    def update_status(self, url: str, status: DownloadStatus) -> None:
        pass
