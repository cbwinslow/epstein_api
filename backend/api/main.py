"""
FastAPI main application entry point.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router
from backend.core.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 10
INITIAL_BACKOFF = 1
MAX_BACKOFF = 30


async def wait_for_redis(settings: Any) -> bool:
    """Wait for Redis to be available with exponential backoff."""
    import redis

    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            client = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                socket_connect_timeout=5,
            )
            client.ping()
            logger.info(
                f"Redis connection successful at {settings.redis.host}:{settings.redis.port}"
            )
            return True
        except Exception as e:
            logger.warning(f"Redis not ready (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
    return False


async def wait_for_neo4j(settings: Any) -> bool:
    """Wait for Neo4j to be available with exponential backoff."""
    from neo4j import GraphDatabase

    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            driver = GraphDatabase.driver(
                settings.neo4j.uri,
                auth=(settings.neo4j.username, settings.neo4j.password),
            )
            driver.verify_connectivity()
            driver.close()
            logger.info(f"Neo4j connection successful at {settings.neo4j.uri}")
            return True
        except Exception as e:
            logger.warning(f"Neo4j not ready (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
    return False


async def wait_for_chromadb(settings: Any) -> bool:
    """Wait for ChromaDB to be available with exponential backoff using heartbeat."""
    import chromadb
    from chromadb.config import Settings

    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            client = chromadb.HttpClient(
                host=settings.chromadb.host,
                port=settings.chromadb.port,
                settings=Settings(anonymized_telemetry=False),
            )
            client.heartbeat()
            logger.info(
                f"ChromaDB connection successful at {settings.chromadb.host}:{settings.chromadb.port}"
            )
            return True
        except Exception as e:
            logger.warning(f"ChromaDB not ready (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Epstein OSINT API")

    settings = get_settings()

    redis_ok = await wait_for_redis(settings)
    if not redis_ok:
        logger.error("Failed to connect to Redis after max retries")
        raise RuntimeError("Redis connection failed")

    neo4j_ok = await wait_for_neo4j(settings)
    if not neo4j_ok:
        logger.error("Failed to connect to Neo4j after max retries")
        raise RuntimeError("Neo4j connection failed")

    chromadb_ok = await wait_for_chromadb(settings)
    if not chromadb_ok:
        logger.error("Failed to connect to ChromaDB after max retries")
        raise RuntimeError("ChromaDB connection failed")

    logger.info("All dependencies ready - API accepting traffic")

    yield
    logger.info("Shutting down Epstein OSINT API")


app = FastAPI(
    title="Epstein OSINT Pipeline",
    description="OSINT Document Analysis & RAG Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "Epstein OSINT Pipeline",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
