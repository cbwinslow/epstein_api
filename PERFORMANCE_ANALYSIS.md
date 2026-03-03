# Performance Analysis - Epstein OSINT Pipeline

## Issues Found & Solutions Applied

### 1. Docker Context Size (8GB+ → ~100MB)
**Problem:** Every build transferred 8GB+ because entire repo including data/ was copied
**Solution:** Created `.dockerignore` files for backend/ and frontend/

### 2. Port Conflicts
**Problem:** Local Redis on port 6379 conflicted with Docker Redis
**Solution:** Removed host port binding from Redis in docker-compose.yml (only internal access needed)

### 3. Build Time Issues
- Worker image takes ~6 minutes due to PyTorch + CUDA downloads
- API image is cached after first build

### 4. Container Memory
- API: ~2GB RAM
- Worker: ~4GB RAM (with GPU libs)
- Neo4j: ~2GB RAM  
- ChromaDB: ~500MB RAM
- Redis: ~50MB RAM
- Frontend: ~200MB RAM

## Quick Start Commands

```bash
# Start (uses cached images if available)
docker compose up -d

# Full rebuild (slow - only when needed)
docker compose build --no-cache
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Future Optimizations (Optional)

1. **Multi-stage builds** - Reduce final image size by 50%
2. **BuildKit cache** - Enable persistent build cache
3. **Pre-built wheels** - Pin PyTorch to CPU version for non-GPU runs
4. **Watchtower** - Auto-update containers

## Key Files Modified
- docker-compose.yml - Fixed Redis port conflict
- backend/.dockerignore - Exclude data/, __pycache__, etc.
- frontend/.dockerignore - Exclude node_modules, .next, etc.
