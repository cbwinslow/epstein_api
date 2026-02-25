# Project Tasks

## Instructions
- **NEVER delete tasks** - Only append new tasks or update status
- Use checkbox format: `- [ ]` for pending, `- [x]` for completed
- Add new tasks at the end of appropriate section

---

## Phase 1: Scaffolding & CI/CD
- [x] Task: Create monorepo folder structure (/backend, /frontend, /data, /docs) - Priority: high - Status: completed
- [x] Task: Generate docker-compose.yml for Neo4j, Redis, ChromaDB - Priority: high - Status: completed
- [x] Task: Generate empty .md documentation files - Priority: medium - Status: completed
- [x] Task: Generate GitHub Actions .yml for issue management - Priority: medium - Status: completed
- [x] Task: Create knowledge_base.md with doc references - Priority: high - Status: completed

---

## Phase 2: Core Interfaces & Config
- [x] Task: Create backend package structure with __init__.py files - Priority: high - Status: completed
- [x] Task: Define Abstract Base Classes (ABCs) for Downloader, Processors, DB Connectors - Priority: high - Status: completed
- [x] Task: Create Pydantic settings configuration (config.yaml + settings.py) - Priority: high - Status: completed
- [x] Task: Setup dependency injection container - Priority: high - Status: completed
- [x] Task: Create core module with protocol definitions - Priority: high - Status: completed
- [x] Task: Create Pydantic entity models (Person, Organization, Aircraft, Location, Event) - Priority: high - Status: completed
- [x] Task: Create service implementation stubs - Priority: high - Status: completed
- [x] Task: Move SQL statements to migrations module - Priority: high - Status: completed
- [x] Task: Update rules.md with comprehensive security/quality rules - Priority: high - Status: completed
- [x] Task: Create custom exception hierarchy (core/exceptions.py) - Priority: high - Status: completed
- [x] Task: Create Pydantic validation schemas (core/schemas.py) - Priority: high - Status: completed
- [x] Task: Set up tests directory with pytest configuration - Priority: high - Status: completed
- [x] Task: Write base unit tests for schemas and exceptions - Priority: high - Status: completed

---

## Phase 3: The Download Manager
- [x] Task: Implement async downloader with chunked downloads - Priority: high - Status: completed
- [x] Task: Implement state ledger with SQLite persistence - Priority: high - Status: completed
- [x] Task: Add WebSocket broadcast for progress tracking - Priority: high - Status: completed
- [x] Task: Implement resume-on-restart functionality - Priority: high - Status: completed
- [x] Task: Add exponential backoff for rate limits - Priority: medium - Status: completed
- [x] Task: Write unit tests for downloader - Priority: high - Status: completed
- [x] Task: Write integration tests for state ledger - Priority: high - Status: completed

---

## Phase 4: Queues & Processing
- [x] Task: Implement Celery workers for background jobs - Priority: high - Status: completed
- [x] Task: Create file router based on MIME types - Priority: high - Status: completed
- [x] Task: Implement PDF text extraction with PyMuPDF - Priority: high - Status: completed
- [x] Task: Implement OCR routing for scanned images - Priority: high - Status: completed
- [x] Task: Integrate Tesseract/Surya for OCR - Priority: medium - Status: completed
- [x] Task: Implement audio transcription with Whisper - Priority: medium - Status: completed
- [x] Task: Create JSON sidecar output for processed files - Priority: high - Status: completed
- [x] Task: Write tests for file processors - Priority: high - Status: completed

---

## Phase 5: Database & RAG
- [x] Task: Implement ChromaDB ingestion pipeline - Priority: high - Status: completed
- [x] Task: Implement semantic text chunking - Priority: high - Status: completed
- [x] Task: Integrate sentence-transformers for embeddings - Priority: high - Status: completed
- [x] Task: Build Neo4j Cypher query builders - Priority: high - Status: completed
- [x] Task: Create entity/relationship CRUD operations - Priority: high - Status: completed
- [x] Task: Write tests for vector database operations - Priority: high - Status: completed
- [x] Task: Write tests for graph database operations - Priority: high - Status: completed

---

## Phase 6: AI Agents
- [x] Task: Setup LangGraph/CrewAI workflows - Priority: high - Status: completed
- [x] Task: Implement Extractor Agent with structured output - Priority: high - Status: completed
- [x] Task: Implement Relationship Analyst Agent - Priority: high - Status: completed
- [x] Task: Implement Query Agent with MCP tools - Priority: high - Status: completed
- [x] Task: Integrate Ollama/OpenRouter LLM - Priority: high - Status: completed
- [x] Task: Write agent behavior tests - Priority: high - Status: completed
- [x] Task: Update ModelRouter with dynamic OpenRouter model fetching - Priority: high - Status: completed
- [x] Task: Add CrewAI orchestrator with sequential agent pipeline - Priority: high - Status: completed
- [x] Task: Implement LangChain tools for MCP (read_sidecar, query_vector_db, search_graph) - Priority: high - Status: completed
- [x] Task: Add TelemetryLogger with SQLite audit trail - Priority: high - Status: completed

---

## Phase 7: The Frontend
- [x] Task: Choose frontend framework (Next.js or Streamlit) - Priority: high - Status: completed
- [x] Task: Initialize Next.js project with Tailwind CSS - Priority: high - Status: completed
- [x] Task: Create layout with sidebar navigation - Priority: high - Status: completed
- [x] Task: Build Dashboard (/) with quick start guide - Priority: high - Status: completed
- [x] Task: Build Settings page (/settings) with model selection - Priority: medium - Status: completed
- [x] Task: Build Ingest page (/ingest) with WebSocket progress - Priority: high - Status: completed
- [x] Task: Build Processing Queue page (/process) - Priority: high - Status: completed
- [x] Task: Build Analysis page (/analyze) with swarm control - Priority: high - Status: completed
- [x] Task: Add API proxy configuration in next.config.ts - Priority: high - Status: completed
- [x] Task: Build Graph Explorer with react-force-graph - Priority: medium - Status: completed
- [ ] Task: Write frontend E2E tests - Priority: medium - Status: pending

---

## Testing & Validation
- [x] Task: Set up pytest configuration - Priority: high - Status: completed
- [x] Task: Set up coverage.py with minimum 80% threshold - Priority: high - Status: completed
- [x] Task: Set up ruff for linting - Priority: high - Status: completed
- [x] Task: Set up mypy for type checking - Priority: high - Status: completed
- [x] Task: Create CI/CD pipeline with all checks - Priority: high - Status: completed
- [x] Task: Achieve 100% coverage on critical paths - Priority: high - Status: completed

---

## Phase 8: Polish & Orchestration
- [x] Task: Create docker-compose.yml with all services - Priority: high - Status: completed
- [x] Task: Create backend Dockerfiles (api + worker) - Priority: high - Status: completed
- [x] Task: Create .env.example - Priority: high - Status: completed
- [x] Task: Create Makefile with startup commands - Priority: high - Status: completed
- [x] Task: Write comprehensive README.md - Priority: high - Status: completed

---

## Documentation
- [ ] Task: Fill in architecture.md - Priority: medium - Status: pending
- [ ] Task: Fill in api.md with endpoint documentation - Priority: medium - Status: pending
- [ ] Task: Fill in usage.md with user guide - Priority: medium - Status: pending
- [ ] Task: Fill in deployment.md - Priority: medium - Status: pending

---

## Notes
- All SQL must be in migrations module (backend/migrations/migrations.py)
- All code must have type hints and docstrings
- All new functionality requires tests
- Follow append-only policy for this file
