# Global Engineering Rules

## 1. Code Quality & Architecture
- **SOLID Principles:** Strict adherence. Use Dependency Injection for database clients and AI model providers so we can easily swap them later.
- **Encapsulation:** Class internals must be hidden. Expose only what is necessary via public methods.
- **Typing:** Python code MUST use strict type hinting. Use Pydantic models for data validation passing between layers.

## 2. State & Error Handling
- **Never Fail Silently:** Catch exceptions, log them with full tracebacks to a local `logs/error.log`, and gracefully update the database state (e.g., mark a download as `FAILED` instead of crashing the app).
- **Idempotency:** All jobs (downloading, vectorizing) must be idempotent. Running the pipeline twice on the same file must not create duplicates in the database.

## 3. GitHub Project Management
- **Issues:** Every bug or missing feature must be logged as a GitHub issue via CLI or API. 
- **Commits:** Use conventional commits (e.g., `feat: async downloader`, `fix: OCR retry logic`).

## 4. Database & SQL Security (CRITICAL)

### 4.1 Never Write Raw SQL in Functions
- **NEVER** embed SQL strings directly in service functions or methods
- **ALWAYS** use the migrations module (`backend/migrations/`) for all SQL statements
- Import SQL from migration files: `from backend.migrations.migrations import get_migration_sql`
- This prevents SQL injection vulnerabilities and keeps code maintainable

### 4.2 Parameterized Queries
- Use parameterized queries with placeholders (`?` for SQLite, `:name` for SQLAlchemy)
- Never use string concatenation or f-strings to build SQL queries
- Example SAFE:
  ```python
  cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
  ```
- Example VULNERABLE (NEVER DO THIS):
  ```python
  cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
  ```

### 4.3 ORM Usage
- Prefer SQLAlchemy ORM or similar ORM frameworks over raw SQL
- Use ORM methods: `.filter()`, `.query()`, `.select()` which auto-parameterize
- Only use raw SQL when absolutely necessary, and always via migration module

### 4.4 Database Migrations
- All schema changes MUST be in `backend/migrations/migrations.py`
- Use versioned migrations with `MigrationVersion` enum
- Include indexes for performance
- Never modify existing migrations; only add new ones

## 5. Code Formatting & Organization

### 5.1 Line Length & Structure
- Maximum line length: 100 characters
- Use blank lines to separate logical sections
- Group imports: standard library, third-party, local modules

### 5.2 File Organization
- One class per file (unless tightly coupled)
- Private methods after public methods
- Constants at module top, after imports
- Type definitions in `models/`

### 5.3 Naming Conventions (PEP 8 + Google Style)
- **Variables:** `snake_case` (e.g., `download_task`, `file_path`)
- **Functions:** `snake_case` (e.g., `get_download_status`, `process_file`)
- **Classes:** `PascalCase` (e.g., `AsyncDownloader`, `SQLiteStateDB`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `CHUNK_SIZE`)
- **Private members:** Prefix with underscore (e.g., `_internal_method`)
- **Booleans:** Prefix with `is_`, `has_`, `can_` (e.g., `is_active`, `has_permission`)

## 6. Documentation Standards

### 6.1 Docstrings (Required for ALL public functions/classes)
```python
def download_file(url: str, dest: Path) -> DownloadTask:
    """Download a file from URL to destination path.
    
    Args:
        url: The URL to download from.
        dest: The destination path for the file.
    
    Returns:
        DownloadTask: The task with status and metadata.
    
    Raises:
        DownloadError: If the download fails after max retries.
    
    Example:
        >>> task = await download_file("https://example.com/file.pdf", Path("./data/file.pdf"))
        >>> task.status
        <DownloadStatus.COMPLETED: 'COMPLETED'>
    """
```

### 6.2 Inline Comments
- Use sparingly and meaningfully
- Explain WHY, not WHAT
- Bad: `# Increment i` (obvious)
- Good: `# Compensate for off-by-one in zero-indexed array`

### 6.3 Module Docstrings
- Every `.py` file MUST have a module docstring at the top
- Describe purpose, usage, and important notes

## 7. Testing Requirements (100% Coverage Mandate)

### 7.1 Test Types Required
1. **Unit Tests:** Test individual functions/methods in isolation
2. **Integration Tests:** Test component interactions
3. **End-to-End Tests:** Test complete workflows
4. **Property-Based Tests:** Use Hypothesis for edge cases
5. **Contract Tests:** Verify API/interface contracts

### 7.2 Test Organization
- Test files in `tests/` directory (parallel to `backend/`)
- Naming: `test_<module>_<function>.py`
- Use pytest framework
- One assertion per test when possible

### 7.3 Coverage Requirements
- **MINIMUM 80% code coverage** required
- **Target: 100%** for critical paths (authentication, data processing)
- Exclude from coverage:
  - `__repr__`, `__str__` methods
  - Simple property getters/setters
  - Legacy compatibility code (documented)
- Run coverage: `pytest --cov=backend --cov-report=html`

### 7.4 Test Best Practices
- Follow AAA pattern: **Arrange**, **Act**, **Assert**
- Use fixtures for shared setup (`conftest.py`)
- Parametrize tests for multiple inputs: `@pytest.mark.parametrize`
- Mock external dependencies (databases, APIs)
- Tests MUST be deterministic (no random values, no timing dependencies)
- Fast execution: unit tests < 100ms each

### 7.5 CI/CD Testing
- Run tests on every push and PR
- Fail build if coverage drops below threshold
- Run linting before tests: `ruff check . && mypy .`

## 8. Security & Vulnerability Prevention

### 8.1 Input Validation
- Validate ALL input at API boundaries
- Use Pydantic models for request/response validation
- Sanitize file paths to prevent directory traversal attacks
- Validate URLs before making requests

### 8.2 Secret Management
- NEVER commit secrets to git (API keys, passwords, tokens)
- Use environment variables or secrets management
- Use `.env.example` for required variables (no real values)

### 8.3 Dependency Security
- Audit dependencies: `pip-audit` or `safety`
- Pin dependency versions in `pyproject.toml`
- Update dependencies regularly

### 8.4 Rate Limiting & DoS Prevention
- Implement exponential backoff for retries
- Add timeouts to all network calls
- Limit request sizes

### 8.5 SQL Security (CRITICAL)
- **NEVER use f-strings or string concatenation for SQL queries**
- **ALWAYS use parameterized queries**: Pass variables through the database driver, not string formatting
- Example SAFE (aiosqlite):
  ```python
  await db.execute(
      "SELECT * FROM tasks WHERE url = ?",
      (url,)  # Parameters passed separately
  )
  ```
- Example SAFE (SQLAlchemy):
  ```python
  db.execute(select(Task).where(Task.url == url))
  ```
- Example VULNERABLE (NEVER DO THIS):
  ```python
  db.execute(f"SELECT * FROM tasks WHERE url = '{url}'")  # SQL INJECTION!
  ```
- All SQL MUST be in migration files, but the migration strings themselves must use parameterization for any dynamic values

### 8.6 Path Traversal Prevention
- When saving downloaded files, aggressively sanitize all filenames and paths
- Ensure a malicious URL cannot force the system to write files outside the designated `/data/downloads` directory
- Reject filenames containing `../` or absolute paths
- Use a whitelist approach: only allow paths within the configured downloads directory

## 9. Task Management (tasks.md)

### 9.1 Append-Only Policy
- **NEVER** delete tasks from `tasks.md`
- Only **append** new tasks or update status
- Use checkbox format: `- [ ] Task description` (pending), `- [x] Task description` (completed)
- Add new tasks at the end of appropriate section

### 9.2 Task Format
```markdown
### Phase X: [Phase Name]
- [ ] Task: [Description] - [Priority: high/medium/low] - [Status: pending/in_progress/completed]
```

### 9.3 Task Updates
- Update status when work begins: `pending` → `in_progress`
- Update status when complete: `in_progress` → `completed`
- Add notes for blockers or progress

## 10. Error Handling & Logging

### 10.1 Logging Standards
- Use `logging` module (not print statements)
- Log levels: DEBUG (detail), INFO (normal), WARNING (issue), ERROR (failure), CRITICAL (system)
- Include context in logs: `logger.info(f"Downloaded {url} to {dest_path}")`
- Never log secrets or PII

### 10.2 Exception Handling
- Catch specific exceptions, not broad `Exception`
- Re-raise with context: `raise DownloadError(f"Failed to download {url}") from original_exception`
- Never suppress errors silently

### 10.3 Error Response
- Return meaningful error messages to users
- Don't expose internal implementation details
- Use proper HTTP status codes in APIs

## 11. Performance & Optimization

### 11.1 Database Queries
- Add indexes for frequently queried columns
- Use connection pooling
- Batch inserts when possible
- Avoid N+1 query patterns

### 11.2 Async/Await
- Use async for I/O operations (network, disk)
- Don't block event loop with sync operations
- Use `asyncio.gather()` for concurrent operations

### 11.3 Memory
- Stream large files instead of loading into memory
- Use generators for large datasets
- Clean up resources (close files, connections)

## 12. API Design

### 12.1 RESTful Principles
- Use proper HTTP methods: GET (read), POST (create), PUT (update), DELETE (delete)
- Use plural nouns for resources: `/api/v1/downloads` not `/api/v1/download`
- Return proper status codes: 200 (OK), 201 (Created), 400 (Bad Request), 404 (Not Found), 500 (Error)

### 12.2 Versioning
- Version APIs: `/api/v1/`, `/api/v2/`
- Maintain backward compatibility within major versions

## 13. Code Review Checklist

Before submitting code, verify:
- [ ] All SQL in migrations module, not in functions
- [ ] Parameterized queries used (no string concatenation)
- [ ] Type hints on all functions
- [ ] Docstrings on all public functions/classes
- [ ] Tests added for new functionality
- [ ] Coverage maintained or improved
- [ ] No secrets committed
- [ ] Linting passes: `ruff check .`
- [ ] Type checking passes: `mypy .`
- [ ] Tests pass: `pytest`
- [ ] tasks.md updated (append only)

## 14. Linting & Type Checking

### 14.1 Tools Required
- **ruff:** Linting (replaces flake8, isort, black)
- **mypy:** Static type checking
- **pytest:** Testing framework

### 14.2 Commands
```bash
# Lint
ruff check .

# Type check
mypy .

# Run tests with coverage
pytest --cov=backend --cov-report=term-missing

# All checks
ruff check . && mypy . && pytest
```

### 14.3 Strict Mode
- Enable all ruff and mypy strict options
- Treat warnings as errors in CI/CD

## 15. Dependency & Environment Management
- **Strictly `uv`:** Never use `pip`, `venv`, or `conda`. 
- **Adding Packages:** Use `uv add <package>` (this updates `pyproject.toml` and `uv.lock` automatically).
- **Running Scripts:** Use `uv run <script.py>` to automatically execute within the isolated virtual environment without needing to manually `source .venv/bin/activate`.
- **Syncing:** Use `uv sync` to ensure the environment matches the lockfile.
