.PHONY: help build up down logs logs-api logs-worker logs-frontend clean restart

help:
	@echo "Epstein OSINT Pipeline - Available Commands"
	@echo ""
	@echo "  make build      - Build all Docker images"
	@echo "  make up         - Start the entire cluster (detached)"
	@echo "  make down       - Stop all containers"
	@echo "  make logs       - View all logs"
	@echo "  make logs-api   - View API logs"
	@echo "  make logs-worker - View worker logs"
	@echo "  make clean      - Remove containers, volumes, and images"
	@echo "  make restart    - Restart the cluster"
	@echo ""

build:
	@echo "Building Docker images..."
	docker compose build

up:
	@echo "Starting the cluster..."
	docker compose up -d
	@echo ""
	@echo "Services starting up..."
	@echo "  API:      http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Neo4j:    http://localhost:7474"
	@echo "  ChromaDB: http://localhost:8001"
	@echo "  Redis:    localhost:6379"

down:
	@echo "Stopping containers..."
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f worker

logs-frontend:
	docker compose logs -f frontend

clean:
	@echo "Cleaning up containers, volumes, and images..."
	docker compose down -v
	docker system prune -f

restart: down up
