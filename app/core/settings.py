from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "Epstein OSINT Pipeline"
    version: str = "0.1.0"
    debug: bool = True


class StorageConfig(BaseModel):
    data_dir: Path = Path("./data")
    downloads_dir: Path = Path("./data/downloads")
    processed_dir: Path = Path("./data/processed")


class DatabaseConfig(BaseModel):
    sqlite_path: Path = Path("./data/state.db")


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0


class CeleryConfig(BaseModel):
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"


class ChromaDBConfig(BaseModel):
    persist_directory: Path = Path("./data/chromadb")


class Neo4jConfig(BaseModel):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "llama2"


class OpenRouterConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemma-2-9b-ite"


class DownloaderConfig(BaseModel):
    max_concurrent: int = 5
    chunk_size: int = 8192
    timeout: int = 300
    max_retries: int = 3
    retry_backoff: float = 2.0


class OCRConfig(BaseModel):
    tesseract_path: str | None = None
    surya_enabled: bool = True
    languages: list[str] = ["eng"]


class VectorizationConfig(BaseModel):
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50


class WebSocketConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8001


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EPSTEIN_",
        env_nested_delimiter="__",
    )

    app: AppConfig = AppConfig()
    storage: StorageConfig = StorageConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    celery: CeleryConfig = CeleryConfig()
    chromadb: ChromaDBConfig = ChromaDBConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    ollama: OllamaConfig = OllamaConfig()
    openrouter: OpenRouterConfig = OpenRouterConfig()
    downloader: DownloaderConfig = DownloaderConfig()
    ocr: OCRConfig = OCRConfig()
    vectorization: VectorizationConfig = VectorizationConfig()
    websocket: WebSocketConfig = WebSocketConfig()

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Settings":
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        return cls(
            app=AppConfig(**data.get("app", {})),
            storage=StorageConfig(**data.get("storage", {})),
            database=DatabaseConfig(**data.get("database", {})),
            redis=RedisConfig(**data.get("redis", {})),
            celery=CeleryConfig(**data.get("celery", {})),
            chromadb=ChromaDBConfig(**data.get("chromadb", {})),
            neo4j=Neo4jConfig(**data.get("neo4j", {})),
            ollama=OllamaConfig(**data.get("ollama", {})),
            openrouter=OpenRouterConfig(**data.get("openrouter", {})),
            downloader=DownloaderConfig(**data.get("downloader", {})),
            ocr=OCRConfig(**data.get("ocr", {})),
            vectorization=VectorizationConfig(**data.get("vectorization", {})),
            websocket=WebSocketConfig(**data.get("websocket", {})),
        )


@lru_cache
def get_settings() -> Settings:
    config_path = Path(__file__).parent / "config.yaml"
    return Settings.from_yaml(config_path)
