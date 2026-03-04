# Architecture Overview

## System Design

The Epstein OSINT Pipeline is a containerized, microservices-based architecture for processing unstructured documents and building a knowledge graph.

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
│                    ┌─────────┴────────┐                         │
│                    │ epstein-network  │                         │
│                    │    (bridge)      │                         │
│                    └─────────┬────────┘                         │
│                              │                                      │
│  ┌──────────────────────────┴──────────────────────────────────┐ │
│  │                     DOCKER CONTAINERS                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │   Frontend   │  │  API/Worker  │  │ Infrastructure│     │ │
│  │  │  (Next.js)   │  │  (FastAPI)   │  │  Services    │     │ │
│  │  │              │  │  (Celery)    │  │ Redis/Neo4j  │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (Next.js)
- **Port:** 3000
- **Purpose:** User interface for document ingestion, processing, and knowledge graph visualization
- **Tech:** Next.js 16, React, TypeScript

### API (FastAPI)
- **Port:** 8000
- **Purpose:** REST API for managing documents, tasks, and querying the knowledge graph
- **Tech:** FastAPI, Pydantic, Celery

### Worker (Celery)
- **Purpose:** Async task processing for downloads and document processing
- **Tech:** Celery, Redis broker
- **GPU Support:** NVIDIA CUDA for OCR acceleration

### Infrastructure Services

| Service | Container | Internal Port | Purpose |
|---------|-----------|---------------|---------|
| Redis | epstein-redis | 6379 | Message broker, caching |
| Neo4j | epstein-neo4j | 7687/7474 | Graph database |
| ChromaDB | epstein-chroma | 8000 | Vector database |

## Data Flow

```
URL Input → Downloads → OCR/Text Extraction → JSON Sidecar
                                              ↓
                                    ┌─────────────────────┘
                                    ↓
                          AI Agent Processing
                                    ↓
                ┌─────────────────────┼─────────────────────┐
                ↓                     ↓                     ↓
            Neo4j Graph         ChromaDB Vector       SQLite Ledger
                ↓                     ↓                     ↓
            Network Graph      Semantic Search        File Status
```

## Directory Structure

```
epstein/
├── app/                    # Main application code
│   ├── api/               # FastAPI routes
│   │   ├── main.py        # API entry point
│   │   ├── ingest.py      # Document ingestion endpoints
│   │   └── __init__.py    # Graph API endpoints
│   ├── workers/           # Celery tasks
│   │   ├── tasks.py       # Download & processing tasks
│   │   ├── celery_app.py  # Celery configuration
│   │   └── db.py          # Database helpers
│   ├── core/              # Core modules
│   │   ├── settings.py    # Configuration
│   │   ├── interfaces.py  # Protocol definitions
│   │   ├── exceptions.py  # Custom exceptions
│   │   ├── downloader.py  # Async downloader
│   │   └── processing/    # Document processing
│   │       ├── extractors.py
│   │       ├── router.py
│   │       └── schemas.py
│   ├── agents/            # AI agents
│   ├── services/          # Database services
│   └── migrations/        # SQL migrations
├── frontend/             # Next.js UI
├── docs/                  # Documentation
├── tests/                 # Test suite
├── docker-compose.yml     # Container orchestration
└── Makefile              # Build commands
```

## Configuration

Configuration is managed via:
1. `config.yaml` - Main configuration file
2. Environment variables - Override config values
3. `pyproject.toml` - Python dependencies

### Key Settings
- `storage.data_dir` - Data storage location
- `redis.host` - Redis connection
- `neo4j.uri` - Neo4j connection
- `chromadb.persist_directory` - ChromaDB storage

## Development

### Running Locally
```bash
# Build and start
docker compose build
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Running Tests
```bash
docker exec epstein-api uv run pytest tests/ -v
```
