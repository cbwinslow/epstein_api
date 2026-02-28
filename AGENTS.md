# AI Agent Context - Epstein OSINT Pipeline

This document provides context and procedures for AI agents working on this codebase.

## Project Overview

**Epstein OSINT Pipeline** is a local, free, open-source OSINT intelligence platform for analyzing massive unstructured document dumps. The system:
- Ingests documents from URLs
- Extracts text using OCR (Tesseract, Surya) and PDF parsing (PyMuPDF, pdfplumber)
- Transcribes audio/video using Whisper
- Extracts entities using AI agents (CrewAI + LangChain)
- Builds a knowledge graph in Neo4j
- Provides semantic search via ChromaDB vector database

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL PORTS                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ :3000    │  │ :8000    │  │ :8001    │  │ :7474/:7687     │  │
│  │ Frontend │  │   API    │  │ ChromaDB │  │     Neo4j       │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │             │             │                 │            │
│       └─────────────┴─────────────┴─────────────────┘            │
│                              │                                      │
│                    ┌─────────┴─────────┐                         │
│                    │   epstein-network  │                         │
│                    │    (bridge)        │                         │
│                    └─────────┬─────────┘                         │
│                              │                                      │
│  ┌──────────────────────────┴──────────────────────────────────┐ │
│  │                     DOCKER CONTAINERS                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │   Frontend    │  │  API/Worker  │  │ Infrastructure│     │ │
│  │  │  (Next.js)   │  │  (FastAPI)   │  │  Services    │     │ │
│  │  │              │  │  (Celery)    │  │ Redis/Neo4j  │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Docker Services

| Service | Container | Internal Port | External Port | Purpose |
|---------|-----------|---------------|---------------|---------|
| Frontend | epstein-frontend | 3000 | 3000 | Next.js UI |
| API | epstein-api | 8000 | 8000 | FastAPI server |
| Worker | epstein-worker | - | - | Celery task queue |
| Redis | epstein-redis | 6379 | 6379 | Message broker |
| Neo4j | epstein-neo4j | 7687/7474 | 7687/7474 | Graph database |
| ChromaDB | epstein-chroma | 8000 | 8001 | Vector database |

## Docker Networking

**IMPORTANT**: All inter-container communication MUST use Docker service names, NOT `localhost`.

### Correct (Docker networking):
```python
# config.yaml
neo4j:
  uri: "bolt://neo4j:7687"  # ✓ Uses Docker service name

redis:
  host: "redis"  # ✓ Uses Docker service name
```

### Incorrect (localhost):
```python
# WRONG - will fail in Docker
neo4j:
  uri: "bolt://localhost:7687"  # ✗ localhost refers to container itself
```

## Configuration

### Environment Variables

The system uses pydantic-settings with the `EPSTEIN_` prefix. Key configurations:

```bash
# Redis (Docker internal)
EPSTEIN_REDIS__HOST=redis
EPSTEIN_REDIS__PORT=6379

# Neo4j (Docker internal)
EPSTEIN_NEO4J__URI=bolt://neo4j:7687
EPSTEIN_NEO4J__USERNAME=neo4j
EPSTEIN_NEO4J__PASSWORD=password

# ChromaDB (Docker internal)
EPSTEIN_CHROMADB__HOST=chromadb
EPSTEIN_CHROMADB__PORT=8000
```

### Config File Precedence

1. Environment variables (highest priority)
2. `backend/config.yaml`
3. Default values in `backend/core/settings.py`

## Code Conventions

### Python

- **Path aliases**: Use `backend.` prefix for imports (e.g., `from backend.api import router`)
- **Settings**: Always use `get_settings()` function with `@lru_cache` decorator
- **Pydantic models**: Use `model_config = {"extra": "forbid"}` to prevent extra fields

### Example - Creating a new API endpoint:

```python
# backend/api/__init__.py or new file in backend/api/
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/yourfeature", tags=["yourfeature"])

class YourResponse(BaseModel):
    model_config = {"extra": "forbid"}
    field: str

@router.get("/endpoint", response_model=YourResponse)
async def your_endpoint():
    return YourResponse(field="value")
```

### Example - Adding a Celery task:

```python
# backend/workers/tasks.py
from backend.workers.celery_app import celery_app

@celery_app.task(name="your_task_name")
def your_task(param: str) -> dict:
    # Task implementation
    return {"status": "completed", "result": param}
```

## API Lifespan (Startup Health Checks)

The API includes robust startup health checks that verify connectivity to:

1. **Redis** - Uses `redis.ping()`
2. **Neo4j** - Uses `driver.verify_connectivity()`  
3. **ChromaDB** - Uses `client.heartbeat()`

Each check has:
- 10 retry attempts
- Exponential backoff (1s → 30s max)
- Raises `RuntimeError` if connection fails

## Entity Types

| Type | Description | Detection |
|------|-------------|-----------|
| PERSON | Individuals | Name patterns, titles |
| ORGANIZATION | Companies, foundations | "Inc", "LLC", "Foundation" |
| LOCATION | Addresses, islands | Geographic patterns |
| AIRCRAFT | Tail numbers | N##### pattern |
| EVENT | Meetings, flights | Context keywords |

## Relationship Depth Matrix

| Score | Level | Criteria |
|-------|-------|----------|
| 1-2 | Incidental | Same document, no interaction |
| 3-4 | Proximity | Same event, different dates |
| 5-6 | Direct Contact | Documented meetings, same flight |
| 7-8 | Professional/Financial | Board memberships, transactions |
| 9-10 | Core Network | Co-defendants, facilitators |

## Common Procedures

### Adding a new environment variable:

1. Add to `backend/config.yaml` with default
2. Add field to appropriate Config class in `backend/core/settings.py`
3. Add to `.env.example`
4. Reference via `settings.your_field` in code

### Adding a new Celery task:

1. Create task in appropriate module under `backend/workers/`
2. Import and register with celery_app
3. Task is automatically discovered (see `celery_app.py`)

### Updating Docker services:

1. Edit `docker-compose.yml`
2. Rebuild affected services: `docker compose build <service>`
3. Restart: `docker compose up -d <service>`

### Running tests:

```bash
# Inside container
docker exec epstein-api uv run pytest tests/ -v

# Locally (requires local Redis/Neo4j)
cd /home/cbwinslow/Documents/epstein
pip install pytest pytest-asyncio fakeredis
python -m pytest tests/ -v
```

## File Paths

- **Config**: `backend/config.yaml`
- **Settings**: `backend/core/settings.py`
- **API routes**: `backend/api/`
- **Workers**: `backend/workers/`
- **Agents**: `backend/agents/`
- **Database clients**: `backend/core/databases/`

## Troubleshooting

### Container won't start:
```bash
# Check logs
docker compose logs <service>

# Check health status
docker ps

# Restart with no cache
docker compose build --no-cache <service>
docker compose up -d <service>
```

### Connection refused errors:
- Ensure using Docker service names (not localhost)
- Check health checks passed: `docker compose ps`
- Verify network: `docker network inspect epstein_epstein-network`

### Import errors:
- Ensure PYTHONPATH is set: `PYTHONPATH=/app/backend`
- Use `uv run python` not bare `python`

## Makefile Commands

```bash
make build      # Build all Docker images
make up         # Start cluster
make down       # Stop cluster
make logs       # View all logs
make logs-api   # API logs only
make logs-worker # Worker logs only
make restart    # Restart cluster
make clean      # Remove everything
```
