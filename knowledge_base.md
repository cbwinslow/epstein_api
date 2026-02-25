# Knowledge Base

## Documentation Files (read before each session)
- `/home/cbwinslow/Documents/epstein/docs/rules.md` - Engineering rules (SOLID, typing, SQL security, testing, formatting)
- `/home/cbwinslow/Documents/epstein/docs/agents.md` - Agent personas + behavior rules (security, testing, task management)
- `/home/cbwinslow/Documents/epstein/docs/architecture.md` - Project architecture
- `/home/cbwinslow/Documents/epstein/docs/api.md` - API documentation
- `/home/cbwinslow/Documents/epstein/docs/usage.md` - User guide
- `/home/cbwinslow/Documents/epstein/docs/deployment.md` - Deployment guide
- `/home/cbwinslow/Documents/epstein/docs/methodology.md` - Entity extraction rules, relationship scoring

## Code References
- `backend/core/interfaces.py` - ABCs and Protocols (DownloaderProtocol, ProcessorProtocol, VectorDBProtocol, GraphDBProtocol, StateDBProtocol)
- `backend/core/settings.py` - Pydantic settings (`get_settings()`)
- `backend/core/container.py` - Dependency injection container
- `backend/core/exceptions.py` - Custom exception hierarchy (OSINTPipelineError base, DownloadError, OCRProcessingError, AgentParsingError, DatabaseConnectionError, etc.)
- `backend/core/schemas.py` - Pydantic validation schemas for AI agent outputs
- `backend/core/downloader.py` - AsyncDownloader with aiohttp, DownloadLedger with aiosqlite, progress streaming
- `backend/config.yaml` - Configuration file
- `backend/migrations/migrations.py` - SQL migrations
- `backend/models/entities.py` - Pydantic entity models
- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_schemas.py` - Unit tests for Pydantic schemas
- `tests/test_exceptions.py` - Unit tests for exceptions
- `tests/test_downloader.py` - Unit tests for async downloader

## Critical Rules Summary (from rules.md)

### SQL Security (MOST IMPORTANT)
1. **NEVER write raw SQL in functions** - Use `backend/migrations/migrations.py`
2. **Always use parameterized queries** - `cursor.execute("SELECT ?", (value,))`
3. **Never concatenate strings for SQL**

### Code Quality
1. **SOLID Principles** - Use Dependency Injection
2. **Strict typing** - All functions need type hints
3. **Docstrings** - All public functions/classes need Google-style docstrings
4. **Naming** - snake_case (vars), PascalCase (classes), UPPER_SNAKE_CASE (constants)

### Testing (100% Coverage Target)
1. **Write tests for ALL new code**
2. **Minimum 80% coverage** required
3. **Follow AAA pattern** - Arrange, Act, Assert
4. **Mock external dependencies**

### Error Handling (from exceptions.py)
1. **Never crash** - Log errors, mark as FAILED, continue processing
2. **Use custom exceptions** - Always raise OSINTPipelineError subclasses
3. **Include context** - Add URL, file path, original exception to details
4. **Auto-logging** - Exceptions automatically log with traceback

### Validation (from schemas.py)
1. **Pydantic V2** - Use for all input/output validation
2. **Strict mode** - `model_config = {"extra": "forbid"}` to reject unknown fields
3. **Patterns** - Use regex for validation (tail numbers, URLs, etc.)
4. **Bounds** - Use Field(ge=, le=) for numeric validation

### Task Management
1. **NEVER delete from tasks.md** - Only append
2. **Use checkbox format** - `- [ ]` pending, `- [x]` completed

### Linting & Type Checking
```bash
ruff check .
mypy .
pytest --cov=backend
```

## Agent Personas (from agents.md)
1. **Extractor Agent** - Parse OCR/PDF, structured JSON, extract entities
2. **Relationship Analyst Agent** - Score relationships 1-10, Cypher queries
3. **Query Agent** - User-facing, MCP for ChromaDB/Neo4j

## Entity Types (from methodology.md)
- **PERSON:** Full names, aliases, titles
- **ORGANIZATION:** Companies, foundations, shell corporations
- **LOCATION:** Addresses, islands, properties
- **AIRCRAFT:** Tail numbers (N228AW, N120JE)
- **DATE/TIME:** Specific dates or inferred ranges
- **EVENT:** Meetings, flights, court depositions

## Relationship Scoring (from methodology.md)
- **Level 1-2 (Incidental):** Same document, no interaction
- **Level 3-4 (Proximity):** Same event, same aircraft different dates
- **Level 5-6 (Direct Contact):** Documented meetings, same flight
- **Level 7-8 (Professional/Financial):** Board memberships, financial ties
- **Level 9-10 (Core Network):** Co-defendants, facilitators, shared ownership

## Project Execution Plan
- Step 1: Scaffolding & CI/CD ✅
- Step 2: Core Interfaces & Config ✅ (with exceptions, validation, tests)
- Step 3: Download Manager ✅ (AsyncDownloader, DownloadLedger, progress streaming)
- Step 4: Queues & Processing (pending)
- Step 5: Database & RAG (pending)
- Step 6: AI Agents (pending)
- Step 7: Frontend (pending)
