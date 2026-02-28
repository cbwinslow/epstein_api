# Epstein OSINT Pipeline

A local, free, open-source OSINT intelligence platform for analyzing massive unstructured document dumps (e.g., DOJ Epstein files). The system ingests documents, extracts entities using AI agents, and builds a knowledge graph for investigative analysis.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI    │────▶│   Celery    │
│  (Next.js)  │     │   (API)     │     │  (Workers)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                    ┌───────┴───────┐    ┌──────┴──────┐
                    ▼               ▼    ▼             ▼
               ┌─────────┐    ┌─────────┐   ┌─────────┐
               │  Neo4j  │    │ ChromaDB│   │  Redis  │
               │ (Graph) │    │ (Vector)│   │(Broker) │
               └─────────┘    └─────────┘   └─────────┘
```

## The UI Funnel (Workflow)

### 1. Ingest & Download (`/ingest`)
- Paste DOJ file URLs (bulk paste supported)
- Start/Pause/Resume download queue
- Real-time WebSocket progress bars
- Download ledger with status tracking

### 2. Processing Queue (`/process`)
- Monitor ETL pipeline (OCR, Text Extraction, Transcription)
- View pending/processing/completed/failed counts
- Manual override: force OCR fallback on failed files

### 3. Analysis & Knowledge Graph (`/analyze`)
- Awaken Swarm: Run CrewAI agent pipeline on JSON sidecars
- View real-time audit trail with agent reasoning traces
- Interactive graph explorer (react-force-graph-2d)
  - Nodes colored by entity type (Person, Organization, Location, Aircraft, Event)
  - Links thickness = relationship depth score (1-10)

### 4. Settings (`/settings`)
- Configure OpenRouter/Ollama models
- Set concurrency limits for downloads and workers

## Quick Start

### Prerequisites
- Docker & Docker Compose
- At least 8GB RAM recommended

### Step 1: Clone and Setup
```bash
# Clone the repository
cd epstein

# Copy environment variables
cp .env.example .env

# Edit .env with your OpenRouter API key (optional but recommended)
# Get one free at https://openrouter.ai/
```

### Step 2: Boot the Cluster
```bash
# Build and start all services
make build
make up

# Or step by step:
docker compose build
docker compose up -d
```

### Step 3: Access the UI
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **ChromaDB**: http://localhost:8001
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, pass: password)

### View Logs
```bash
# All logs
make logs

# Specific service
make logs-api
make logs-worker
make logs-frontend
```

### Stop the Cluster
```bash
make down
```

## Project Structure

```
epstein/
├── backend/           # FastAPI + Celery
│   ├── api/          # API routes
│   ├── agents/       # CrewAI agents
│   ├── core/         # Config, DB clients, processing
│   ├── databases/    # Neo4j, ChromaDB clients
│   └── workers/      # Celery tasks
├── frontend/         # Next.js 14 (App Router)
│   └── src/
│       ├── app/      # Pages: /, /ingest, /process, /analyze, /settings
│       └── components/
├── docs/             # Documentation
├── data/             # Shared data (downloads, processed, SQLite ledger)
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| PERSON | Individuals | Jeffrey Epstein, Prince Andrew |
| ORGANIZATION | Companies, foundations | JEP Holdings, Nexus Foundation |
| LOCATION | Addresses, islands | Little St. James, Palm Beach |
| AIRCRAFT | Tail numbers | N977AJ, N212JE |
| EVENT | Meetings, flights | Flight logs, depositions |

## Relationship Depth Matrix

| Score | Level | Description |
|-------|-------|-------------|
| 1-2 | Incidental | Same document, no interaction |
| 3-4 | Proximity | Same event, different dates |
| 5-6 | Direct Contact | Documented meetings, same flight |
| 7-8 | Professional/Financial | Board memberships, transactions |
| 9-10 | Core Network | Co-defendants, facilitators |

## Technology Stack

- **API**: FastAPI + Uvicorn
- **Workers**: Celery + Redis
- **Graph DB**: Neo4j
- **Vector DB**: ChromaDB + sentence-transformers
- **AI Agents**: CrewAI + LangChain + OpenRouter
- **Frontend**: Next.js 14 + Tailwind CSS + shadcn/ui
- **Visualization**: react-force-graph-2d

## License

MIT
