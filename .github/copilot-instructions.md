# GitHub Copilot Instructions

## Project Context

You are working on the **Epstein OSINT Pipeline** - a document analysis and RAG system for intelligence gathering.

## Key Files

- `backend/config.yaml` - Single source of truth for configuration
- `backend/core/processing/schemas.py` - Pydantic validation schemas
- `docs/rules.md` - Engineering rules (SOLID, SQL security, testing)
- `docs/agents.md` - Agent personas and behavior rules

## Critical Rules

### SQL Security (MUST FOLLOW)
- NEVER write raw SQL in functions - use `backend/migrations/migrations.py`
- Always use parameterized queries - `cursor.execute("SELECT ?", (value,))`
- Never concatenate strings for SQL

### Code Quality
- Use SOLID Principles with Dependency Injection
- Strict typing - all functions need type hints
- Docstrings required - Google-style for public functions
- Naming: snake_case (vars), PascalCase (classes), UPPER_SNAKE_CASE (constants)

### Testing Requirements
- Minimum 80% code coverage required
- Follow AAA pattern: Arrange, Act, Assert
- Mock external dependencies

### Error Handling
- Never crash - Log errors, mark as FAILED, continue processing
- Use custom exceptions from `backend/core/exceptions.py`
- Always raise OSINTPipelineError subclasses

### Validation
- Use Pydantic V2 for all input/output validation
- Strict mode: `model_config = {"extra": "forbid"}`

## Agent Personas

1. **Extractor Agent** - Parse OCR/PDF, structured JSON, extract entities
2. **Relationship Analyst Agent** - Score relationships 1-10, generate Cypher queries
3. **Query Agent** - User-facing, MCP for ChromaDB/Neo4j

## Important Commands

```bash
# Lint
ruff check .

# Type check
mypy .

# Run tests
pytest --cov=backend

# Orchestrate
python orchestrate.py
```

## Before Writing Code

1. Check `docs/rules.md` and `docs/agents.md` for current conventions
2. Check `knowledge_base.md` for existing patterns
3. Ensure SQL goes through migrations module
4. Add tests for new functionality
