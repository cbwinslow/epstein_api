# Contributing to Epstein OSINT Pipeline

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/epstein_api.git`
3. Install dependencies: `cd backend && uv sync`

## Development Setup

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- uv (package manager)

### Running Locally
```bash
# Start infrastructure
docker compose up -d

# Run the orchestrator
python orchestrate.py

# Run tests
cd backend && uv run pytest
```

## Code Style

We follow these conventions (see `docs/rules.md` for full details):

- **Type hints** required on all functions
- **Docstrings** required on all public functions/classes (Google style)
- **Naming**: snake_case (vars), PascalCase (classes), UPPER_SNAKE_CASE (constants)
- **SOLID Principles** with Dependency Injection

## Testing

- Minimum 80% code coverage required
- Run tests: `pytest --cov=backend`
- Follow AAA pattern: Arrange, Act, Assert

## SQL Guidelines

- NEVER write raw SQL in functions
- Use `backend/migrations/migrations.py` for all SQL
- Always use parameterized queries

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run linting: `ruff check . && mypy .`
4. Run tests: `pytest`
5. Commit with conventional commits: `feat: add new feature`
6. Push and create PR

## Commit Messages

We use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance

## Questions?

Open an issue for questions about contributing.
