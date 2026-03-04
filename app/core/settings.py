from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "Epstein OSINT Pipeline"
    version: str = "0.1.0"
    debug: bool = True


class StorageConfig(BaseModel):
    data_dir: Path = Path("./data")
    downloads_dir: Path = Path("./data/downloads")
    processed_dir: Path = Path("./data/processed")

    @model_validator(mode="after")
    def resolve_paths(self):
        """Resolve paths based on environment or Docker mount."""
        # Check env var first
        data_dir = os.environ.get("EPSTEIN_STORAGE__DATA_DIR")
        if not data_dir:
            # Check if /data exists (Docker mount)
            if Path("/data").exists():
                data_dir = "/data"
            else:
                data_dir = str(self.data_dir)

        self.data_dir = Path(data_dir)
        self.downloads_dir = self.data_dir / "downloads"
        self.processed_dir = self.data_dir / "processed"
        return self


class DatabaseConfig(BaseModel):
    sqlite_path: Path = Path("./data/state.db")

    @model_validator(mode="after")
    def resolve_path(self):
        """Resolve path based on environment or Docker mount."""
        # Check env var first
        sqlite_path = os.environ.get("EPSTEIN_DATABASE__SQLITE_PATH")
        if not sqlite_path:
            # Check if /data exists (Docker mount)
            if Path("/data").exists():
                sqlite_path = "/data/state.db"
            else:
                sqlite_path = str(self.sqlite_path)

        self.sqlite_path = Path(sqlite_path)
        return self


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_REDIS__", extra="ignore")
    host: str = "localhost"
    port: int = 6379
    db: int = 0


class CeleryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_CELERY__", extra="ignore")
    broker_url: str = ""  # Will be set from redis settings if empty
    result_backend: str = ""  # Will be set from redis settings if empty
    
    @model_validator(mode="after")
    def resolve_from_redis(self):
        """If broker_url/result_backend not set, derive from redis settings."""
        if not self.broker_url:
            self.broker_url = "redis://redis:6379/0"
        if not self.result_backend:
            self.result_backend = "redis://redis:6379/0"
        return self


class ChromaDBConfig(BaseModel):
    persist_directory: Path = Path("./data/chromadb")

    @model_validator(mode="after")
    def resolve_path(self):
        """Resolve path based on environment or Docker mount."""
        # Check env var first
        persist_dir = os.environ.get("EPSTEIN_CHROMADB__PERSIST_DIRECTORY")
        if not persist_dir:
            # Check if /data exists (Docker mount)
            if Path("/data").exists():
                persist_dir = "/data/chromadb"
            else:
                persist_dir = str(self.persist_directory)

        self.persist_directory = Path(persist_dir)
        return self


class Neo4jConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_NEO4J__", extra="ignore")
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class OllamaConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_OLLAMA__", extra="ignore")
    base_url: str = "http://localhost:11434"
    model: str = "llama2"


class OpenRouterConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_OPENROUTER__", extra="ignore")
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemma-2-9b-ite"


class DownloaderConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_DOWNLOADER__", extra="ignore")
    max_concurrent: int = 5
    chunk_size: int = 8192
    timeout: int = 300
    max_retries: int = 3
    retry_backoff: float = 2.0
    # DOJ Age Verification Cookies
    justice_gov_age_verified: str = "true"
    ak_bmsc: str = ""
    queue_it_accepted: str = ""


class OCRConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_OCR__", extra="ignore")
    tesseract_path: str | None = None
    surya_enabled: bool = True
    languages: list[str] = ["eng"]


class VectorizationConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_VECTORIZATION__", extra="ignore")
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50


class WebSocketConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EPSTEIN_WEBSOCKET__", extra="ignore")
    host: str = "0.0.0.0"
    port: int = 8001


class Settings(BaseSettings):
    """Main settings class.
    
    Environment variables take precedence over config.yaml values.
    Use EPSTEIN_ prefix with double underscore for nested:
      EPSTEIN_REDIS__HOST=redis
      EPSTEIN_STORAGE__DATA_DIR=/data
    """
    model_config = SettingsConfigDict(
        env_prefix="EPSTEIN_",
        env_nested_delimiter="__",
        extra="ignore",
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
        """Load settings from YAML file.
        
        Note: Nested configs (redis, celery, etc.) are initialized from environment
        variables, not from YAML. Only app-level settings come from YAML.
        """
        config_path = Path(path)
        
        # Always create fresh instances - env vars take precedence
        # Only app-level config can come from YAML
        app_data = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data: dict[str, Any] = yaml.safe_load(f) or {}
                    app_data = data.get("app", {})
            except Exception:
                pass
        
        return cls(
            app=AppConfig(**app_data),
        )


def _find_config_path() -> Path:
    """Find config.yaml in standard locations.
    
    Searches in order:
    1. EPSTEIN_CONFIG_PATH environment variable
    2. Current working directory
    3. Script directory (for Docker    4. Project root (parent)
 of app directory)
    """
    # Check environment variable first
    config_from_env = os.environ.get("EPSTEIN_CONFIG_PATH")
    if config_from_env:
        config_path = Path(config_from_env)
        if config_path.exists():
            return config_path.resolve()
    
    # Check current directory
    config_path = Path("./config.yaml")
    if config_path.exists():
        return config_path.resolve()
    
    # Check script directory (Docker: /app/config.yaml)
    script_dir = Path(__file__).parent.parent
    config_path = script_dir / "config.yaml"
    if config_path.exists():
        return config_path.resolve()
    
    # Check parent of script directory (project root)
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config.yaml"
    if config_path.exists():
        return config_path.resolve()
    
    # Return default path (will use YAML defaults if not found)
    return script_dir / "config.yaml"


def _detect_environment() -> str:
    """Detect if running in Docker or locally.
    
    Returns:
        "docker" - Running in Docker container
        "windows" - Running on Windows locally
        "linux" - Running on Linux/macOS locally
    """
    # Check for Docker indicators
    if Path("/.dockerenv").exists() or os.environ.get("DOCKER_CONTAINER"):
        return "docker"
    
    # Check for Windows
    if os.name == "nt" or os.environ.get("OS", "").startswith("Windows"):
        return "windows"
    
    return "linux"


@lru_cache
def get_settings() -> Settings:
    """Get application settings.
    
    Uses EPSTEIN_CONFIG_PATH env var, config.yaml, or defaults.
    Path resolution works automatically for Docker and local (Windows/Linux).
    """
    config_path = _find_config_path()
    env_type = _detect_environment()
    
    # For Docker, check if /data exists and use absolute paths
    if env_type == "docker":
        if Path("/data").exists():
            # Update defaults for Docker
            os.environ.setdefault("EPSTEIN_STORAGE__DATA_DIR", "/data")
            os.environ.setdefault("EPSTEIN_DATABASE__SQLITE_PATH", "/data/state.db")
            os.environ.setdefault("EPSTEIN_CHROMADB__PERSIST_DIRECTORY", "/data/chromadb")
    
    return Settings.from_yaml(config_path)
