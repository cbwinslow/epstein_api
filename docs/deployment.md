# Deployment Guide

## Prerequisites

- Docker & Docker Compose
- At least 8GB RAM recommended
- NVIDIA GPU (optional, for accelerated OCR)

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd epstein

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Required: OPENROUTER_API_KEY
```

### 2. Build and Start

```bash
# Build all images
docker compose build

# Start all services
docker compose up -d
```

### 3. Verify

```bash
# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
| ChromaDB | http://localhost:8001 |

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

## Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...

# Neo4j (Docker internal)
EPSTEIN_NEO4J__URI=bolt://neo4j:7687
EPSTEIN_NEO4J__PASSWORD=password

# Redis (Docker internal)
EPSTEIN_REDIS__HOST=redis
EPSTEIN_REDIS__PORT=6379
```

### Configuration File

Edit `app/config.yaml` for detailed settings:

- Storage paths
- Downloader settings
- OCR configuration
- Vectorization model
- Worker concurrency

## Docker Services

### API Service
- FastAPI server
- Handles REST endpoints
- No GPU required

### Worker Service
- Celery task workers
- Processes documents
- **GPU support available** (requires nvidia-docker)

### Frontend Service
- Next.js web UI
- Port 3000

### Infrastructure

| Service | Image | Purpose |
|---------|-------|---------|
| Redis | redis:7-alpine | Message broker |
| Neo4j | neo4j:5.14-community | Graph database |
| ChromaDB | chromadb/chroma:latest | Vector database |

## GPU Setup (Optional)

For GPU-accelerated OCR:

1. Install nvidia-docker:
```bash
# Ubuntu
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

2. Verify:
```bash
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

The worker service is configured to use GPU if available.

## Data Persistence

Data is stored in Docker volumes:

- `redis_data` - Redis persistence
- `neo4j_data` - Neo4j database
- `chroma_data` - ChromaDB vectors
- `./data` (host) - Downloads and SQLite database

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs <service>

# Restart with no cache
docker compose build --no-cache <service>
docker compose up -d <service>
```

### Connection refused
- Ensure using Docker service names (not localhost)
- Check health checks: `docker compose ps`
- Verify network: `docker network inspect epstein_epstein-network`

### Out of memory
- Reduce worker concurrency in config
- Limit concurrent downloads

## Production Considerations

1. **Security**
   - Change default passwords
   - Use secrets management
   - Enable SSL/TLS

2. **Monitoring**
   - Add Prometheus metrics
   - Set up Grafana dashboards
   - Configure logging aggregation

3. **Backups**
   - Backup Neo4j data volume
   - Backup ChromaDB vectors
   - Backup SQLite database

4. **Scaling**
   - Run multiple worker instances
   - Use external Redis for multi-node
   - Consider Kubernetes for large deployments
