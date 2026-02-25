from typing import Any, Callable, TypeVar

from backend.core.interfaces import (
    DownloaderProtocol,
    GraphDBProtocol,
    ProcessorProtocol,
    StateDBProtocol,
    VectorDBProtocol,
)
from backend.core.settings import Settings, get_settings


T = TypeVar("T")


class DIContainer:
    def __init__(self) -> None:
        self._services: dict[type, Callable[..., Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._settings: Settings | None = None

    def register(self, interface: type[T], factory: Callable[..., T]) -> None:
        self._services[interface] = factory

    def register_singleton(self, interface: type[T], instance: T) -> None:
        self._singletons[interface] = instance

    def resolve(self, interface: type[T]) -> T:
        if interface in self._singletons:
            return self._singletons[interface]

        if interface not in self._services:
            raise KeyError(f"No factory registered for {interface}")

        factory = self._services[interface]
        return factory()

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings


_container: DIContainer | None = None


def get_container() -> DIContainer:
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def register_default_services(container: DIContainer) -> None:
    from backend.services.downloader import AsyncDownloader
    from backend.services.state_db import SQLiteStateDB
    from backend.services.vector_db import ChromaDBClient
    from backend.services.graph_db import Neo4jClient

    container.register(DownloaderProtocol, lambda: AsyncDownloader(container.settings))
    container.register(StateDBProtocol, lambda: SQLiteStateDB(container.settings))
    container.register(VectorDBProtocol, lambda: ChromaDBClient(container.settings))
    container.register(GraphDBProtocol, lambda: Neo4jClient(container.settings))
