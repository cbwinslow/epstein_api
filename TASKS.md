# Project Tasks - Epstein OSINT Pipeline

## Overview

This file tracks ongoing development tasks, bugs, and feature requests for the Epstein OSINT Pipeline.

---

## Quick Reference

### Launch Commands
```bash
# Full rebuild and start
docker compose build
docker compose up -d

# Using Makefile
make build && make up

# View status
docker compose ps

# View logs
docker compose logs -f
```

### Service URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |
| Neo4j | http://localhost:7474 |

---

## Active Issues

### Priority: High

- [ ] **Test the full pipeline** - End-to-end test from ingest to knowledge graph

### Priority: Medium

- [ ] **Add unit tests** - Create test coverage for core modules
- [ ] **Document API endpoints** - Expand OpenAPI documentation
- [ ] **Add monitoring** - Prometheus/Grafana integration

### Priority: Low

- [ ] **Optimize OCR** - Add GPU acceleration for Tesseract
- [ ] **Add caching** - Redis caching for frequent queries
- [ ] **Improve UI** - Add dark mode, better loading states

---

## Completed Tasks

### 2026-02-28

- [x] Fix Neo4j Docker URI (localhost → neo4j)
- [x] Add robust API startup health checks
- [x] Fix ChromaDB configuration
- [x] Add JSON parsing robustness to model router
- [x] Create comprehensive .env.example
- [x] Add Docker healthcheck configurations
- [x] Create AGENTS.md for AI context
- [x] Push all changes to GitHub

---

## Development Workflow

### 1. Making Changes

```bash
# Make code changes in backend/ directory
# Test locally first
docker exec epstein-api uv run python -c "import backend.your_module"

# Rebuild affected services
docker compose build api
docker compose up -d api

# Check logs
docker compose logs -f api
```

### 2. Running Tests

```bash
# Inside container
docker exec epstein-api uv run pytest tests/ -v

# With coverage
docker exec epstein-api uv run pytest tests/ --cov=backend --cov-report=term-missing
```

### 3. Linting

```bash
# Install ruff in container
docker exec epstein-api uv pip install ruff

# Run linting
docker exec epstein-api uv run ruff check backend/
```

### 4. Committing Changes

```bash
# Check status
git status

# Add and commit
git add -A
git commit -m "fix: description of changes"

# Push
git push origin master
```

---

## Known Issues

### Neo4j Password
- Default password is `password`
- Stored in `NEO4J_AUTH` environment variable
- Can be changed in docker-compose.yml

### Port Conflicts
- Port 8000: API
- Port 8001: ChromaDB (external)
- Port 3000: Frontend

If ports are in use, check:
```bash
docker ps | grep -E "8000|8001|3000"
lsof -i :8000
```

### GPU Access (Worker)
- Requires NVIDIA GPU with nvidia-docker installed
- Check with: `docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi`

---

## Environment Variables

### Required
```
OPENROUTER_API_KEY=sk-or-v1-...  # Get from https://openrouter.ai/
NEO4J_PASSWORD=password
```

### Optional
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

---

## Architecture Notes

### Data Flow

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

### Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Container orchestration |
| `backend/config.yaml` | Main configuration |
| `backend/api/main.py` | FastAPI application |
| `backend/workers/tasks.py` | Celery tasks |
| `backend/agents/` | AI agent implementations |

---

## Getting Help

1. Check logs: `docker compose logs -f <service>`
2. Check container health: `docker ps`
3. Verify network: `docker network inspect epstein_epstein-network`
4. Test API: `curl http://localhost:8000/health`

---

*Last updated: 2026-02-28*
