# Epstein OSINT Pipeline — Codebase Review & AI Agent Task List

**Reviewed:** 2026-03-03  
**Reviewer:** GitHub Copilot Automated Review  
**Scope:** Full codebase audit covering security, linting, architecture, correctness, and maintainability.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Security Vulnerabilities](#2-security-vulnerabilities)
3. [Linting Errors (Ruff)](#3-linting-errors-ruff)
4. [Architectural Issues](#4-architectural-issues)
5. [Correctness Bugs](#5-correctness-bugs)
6. [Code Quality Recommendations](#6-code-quality-recommendations)
7. [Test Coverage Gaps](#7-test-coverage-gaps)
8. [AI Agent Task List](#8-ai-agent-task-list)

---

## 1. Executive Summary

| Category | Count | Severity |
|---|---|---|
| Security vulnerabilities | 7 | 🔴 Critical / 🟠 High |
| Linting errors (ruff default rules) | 64 | 🟡 Medium |
| Linting warnings (extended rules) | ~700 | 🟢 Low |
| Architectural issues | 6 | 🟠 High |
| Correctness bugs | 3 | 🔴 Critical |
| Missing test coverage | 4 areas | 🟠 High |

The codebase has a solid foundation with good use of Pydantic schemas, parameterized SQL queries, and a proper custom exception hierarchy. The main risks are an overly permissive CORS configuration, hardcoded credentials in version-controlled files, a Cypher query bug that silently ignores the `rel_type` parameter, and a large number of auto-fixable linting errors.

---

## 2. Security Vulnerabilities

### SEC-01 🔴 Wildcard CORS (`allow_origins=["*"]`)

**Files:** `backend/api/main.py:135`, `app/api/main.py:35`

**Problem:** The API allows requests from any origin. With `allow_credentials=True` (also set), browsers will send cookies/auth headers to any origin. This is a known security misconfiguration.

**Fix:**
```python
# backend/api/main.py  — replace the CORSMiddleware block
import os

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

Add to `docker-compose.yml`:
```yaml
environment:
  - ALLOWED_ORIGINS=http://localhost:3000
```

---

### SEC-02 🔴 Hardcoded Neo4j Password in Version-Controlled Files

**Files:** `backend/config.yaml:31`, `docker-compose.yml:30,36,65,90`

**Problem:** The Neo4j password `"password"` is committed to the repository in `config.yaml` and `docker-compose.yml`. Anyone with repository access can authenticate directly to the graph database.

**Fix — `backend/config.yaml`:**
```yaml
neo4j:
  uri: "bolt://neo4j:7687"
  username: "neo4j"
  password: "${NEO4J_PASSWORD}"   # read from environment
  database: "neo4j"
```

**Fix — `docker-compose.yml`:**
```yaml
neo4j:
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
  ...
api:
  environment:
    - NEO4J_PASSWORD=${NEO4J_PASSWORD}
```

Add `NEO4J_PASSWORD=` to `.env` (already gitignored) and document in `.env.example`:
```bash
NEO4J_PASSWORD=change_this_strong_password
```

---

### SEC-03 🟠 No Authentication on Any API Endpoint

**Files:** `backend/api/__init__.py`, `backend/api/main.py`

**Problem:** All API endpoints are publicly accessible with no authentication mechanism. The `/api/graph/network`, `/api/graph/node/{node_name}`, and `/api/graph/stats` endpoints expose sensitive OSINT data without any access control.

**Fix — Add API key authentication:**
```python
# backend/api/auth.py (new file)
import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    """Dependency that validates the X-API-Key header."""
    expected = os.environ.get("API_KEY")
    if not expected:
        return "no-auth"  # auth disabled when API_KEY not set
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key
```

Apply to every router:
```python
from backend.api.auth import require_api_key
from fastapi import Depends

@router.get("/network", dependencies=[Depends(require_api_key)])
async def get_network_graph(...):
    ...
```

---

### SEC-04 🟠 `DatabaseConnectionError` Leaks Internal Connection Strings

**File:** `backend/core/exceptions.py:203`

**Problem:** `DatabaseConnectionError` stores and logs `connection_string` in plain text. If the connection string contains a password (e.g., `bolt+ssc://neo4j:password@host:7687`), this appears in logs and API error responses.

**Fix:**
```python
class DatabaseConnectionError(DatabaseError):
    def __init__(
        self,
        database_type: str,
        connection_string: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.database_type = database_type
        # Scrub credentials from connection string before storing/logging
        from urllib.parse import urlparse, urlunparse
        try:
            parsed = urlparse(connection_string)
            safe_url = urlunparse(parsed._replace(netloc=parsed.hostname or ""))
        except Exception:
            safe_url = "<redacted>"
        self.connection_string = safe_url
        super().__init__(
            message=f"Failed to connect to {database_type} database",
            details={"database_type": database_type, "connection_string": safe_url},
            original_exception=original_exception,
        )
```

---

### SEC-05 🟠 Cypher Relationship Type Parameter Bug (Silent Injection Risk)

**File:** `backend/core/databases/neo4j_client.py:275-286`

**Problem:** In `find_relationships()`, the Cypher query uses `$rel_type` as a relationship type parameter, but **Cypher does not support parameterizing relationship type labels**. The `$rel_type` placeholder is silently ignored by Neo4j. As a result:
1. The filter is never applied — all relationships are returned regardless of `rel_type`.
2. If this is ever "fixed" naively by string concatenation, it becomes a Cypher injection vulnerability.

**Fix — Use an allowlist and string formatting (safe because it's from an enum):**
```python
from backend.core.schemas import RelationshipType

def find_relationships(
    self,
    entity_name: str,
    rel_type: RelationshipType | None = None,
) -> list[dict[str, Any]]:
    """Find all relationships for an entity."""
    if rel_type is not None:
        # rel_type is validated as a RelationshipType enum — safe to embed
        cypher = f"""
        MATCH (p {{name: $name}})-[r:{rel_type.value}]->(target)
        RETURN p, r, target
        """
    else:
        cypher = """
        MATCH (p {name: $name})-[r]->(target)
        RETURN p, r, target
        """
    return self.execute_query(cypher, {"name": entity_name})
```

---

### SEC-06 🟠 Unvalidated Path Traversal in Sidecar Loading

**File:** `backend/agents/mcp_tools.py:35-55` (`read_sidecar` method)

**Problem:** The `read_sidecar` method accepts `data_dir` as a string override without validation. A caller could pass `data_dir="../../etc"` to read files outside the intended directory.

**Fix:**
```python
def read_sidecar(self, file_id: int, data_dir: str | None = None) -> dict[str, Any]:
    base = Path(data_dir or str(self._settings.storage.data_dir)).resolve()
    search_path = base / "processed"
    # Ensure resolved path stays within the base data directory
    if not str(search_path).startswith(str(base)):
        raise ValueError(f"data_dir resolves outside allowed base: {search_path}")
    ...
```

---

### SEC-07 🟢 `app/` Directory is an Exact Duplicate of `backend/`

**Files:** `app/` directory

**Problem:** The `app/` directory mirrors `backend/` (same files, same structure). Having two copies of the same code creates a security maintenance burden: patches and fixes applied to `backend/` may not be applied to `app/`, leaving `app/` vulnerable.

**Fix:** Delete the `app/` directory and update `docker-compose.yml` to point API and Worker builds to `./backend`:
```yaml
api:
  build:
    context: ./backend
    dockerfile: Dockerfile
```

---

## 3. Linting Errors (Ruff)

Running `ruff check .` inside `backend/` reveals **64 errors** (61 auto-fixable). All auto-fixable errors can be resolved by running:

```bash
cd backend && uv run ruff check . --fix
```

### Summary by Rule

| Rule | Count | Description | Auto-fix |
|---|---|---|---|
| `F401` | 30 | Unused imports | ✅ Yes |
| `F541` | 30 | f-string missing placeholders | ✅ Yes |
| `COM812` | 60 | Missing trailing comma | ✅ Yes |
| `D413` | 76 | Missing blank line after last docstring section | ✅ Yes |
| `G004` | 92 | Logging uses f-string (use `%` or `lazy_format`) | ❌ Manual |
| `BLE001` | 24 | Blind `except Exception` | ❌ Manual |
| `PLC0415` | 22 | Import outside top level | ❌ Manual |
| `TRY400` | 21 | `logger.error()` in except without `logger.exception()` | ❌ Manual |
| `E501` | 15 | Line too long (>100 chars) | ❌ Manual |
| `W291/W293` | 19 | Trailing whitespace | ✅ Yes |
| `I001` | 14 | Unsorted imports | ✅ Yes |
| `PIE790` | 17 | Unnecessary `pass` | ✅ Yes |

### Specific Auto-fixable Unused Imports

| File | Unused Import |
|---|---|
| `agents/fact_extractor.py` | `ExtractedEntitiesOutput` |
| `agents/mcp_tools.py` | `datetime`, `timezone`, `timedelta`, `sidecar_exists` |
| `agents/telemetry.py` | `timedelta` |
| `core/container.py` | `ProcessorProtocol` |
| `core/databases/chroma_client.py` | `Path`, `DatabaseConnectionError` |
| `core/downloader.py` | `re`, `dataclasses.field`, `HashMismatchError`, `os` |
| `services/state_db.py` | `Any`, `StateDBProtocol`, `MigrationVersion`, `get_migration_sql` |
| `services/vector_db.py` | `ChromaSettings`, `VectorDBProtocol` |
| `workers/tasks.py` | `ExtractionMethod`, `ProcessingResult` |

### Manual Fixes Required — Logging Anti-patterns (G004)

Replace f-strings in logging calls with `%`-formatting or `lazy_format` for performance (avoids string construction when log level is disabled):

```python
# Bad (current)
logger.info(f"Processing file {file_id}: {file_path}")

# Good
logger.info("Processing file %s: %s", file_id, file_path)
```

Files affected: `agents/fact_extractor.py`, `agents/mcp_tools.py`, `agents/telemetry.py`, `core/databases/neo4j_client.py`, `workers/tasks.py`, and others.

### Manual Fixes Required — Blind Except (BLE001)

```python
# Bad (current) — hides unexpected exceptions
except Exception:
    continue

# Good — log unexpected exceptions
except Exception:
    logger.debug("Unexpected error reading sidecar: %s", exc_info=True)
    continue
```

---

## 4. Architectural Issues

### ARCH-01 🟠 Global Mutable Singletons Without Thread Safety

**Files:** `backend/api/__init__.py:19-22`, `backend/agents/fact_extractor.py:30-35`

**Problem:** Module-level global variables (`_neo4j_client`, `_mcp_tools_instance`, `_telemetry_instance`) are initialized lazily without locking. Under concurrent requests this can result in multiple instances being created, or partially-initialized objects being observed by other threads.

**Fix:** Use FastAPI's dependency injection with `@lru_cache` or a proper DI container (one already exists in `backend/core/container.py` — use it!):

```python
# backend/api/__init__.py
from functools import lru_cache
from backend.core.settings import get_settings

@lru_cache(maxsize=1)
def _get_neo4j_client() -> Neo4jClient:
    return Neo4jClient(get_settings())

async def get_neo4j() -> Neo4jClient:
    return _get_neo4j_client()
```

---

### ARCH-02 🟠 SQLite Connection Never Closed (Resource Leak)

**File:** `backend/services/state_db.py:29-33`

**Problem:** `SQLiteStateDB` opens a `sqlite3.Connection` and stores it as `self._conn`. The `close()` method exists but is never called in cleanup code. The connection is also not thread-safe (SQLite connections are not safe to share across threads by default).

**Fix:**
```python
def _get_conn(self) -> sqlite3.Connection:
    if self._conn is None:
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,  # explicit flag
        )
        self._conn.row_factory = sqlite3.Row
    return self._conn

def __del__(self) -> None:
    self.close()
```

Register cleanup in the FastAPI lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    yield
    # cleanup
    db = get_container().resolve(StateDBProtocol)
    db.close()
```

---

### ARCH-03 🟠 `celery_app.py` Calls `get_settings()` at Module Import Time

**File:** `backend/workers/celery_app.py:12-14`

**Problem:** `settings = get_settings()` runs when the module is imported, which happens at application startup before environment variables from Docker are fully propagated. This can cause Celery to connect to `localhost` instead of the Docker service name.

**Fix:** Use lazy initialization:
```python
# backend/workers/celery_app.py
from celery import Celery

celery_app = Celery("epstein_osint")

@celery_app.on_after_configure.connect
def _configure(sender, **kwargs):
    from backend.core.settings import get_settings
    settings = get_settings()
    sender.conf.update(
        broker_url=settings.celery.broker_url,
        result_backend=settings.celery.result_backend,
        include=["backend.workers.tasks"],
        ...
    )
```

---

### ARCH-04 🟠 `app/` and `backend/` Are Duplicate Directories

**Problem:** The repository contains two near-identical application directories: `app/` and `backend/`. `docker-compose.yml` builds the API from `./app`, while all Python imports and tests reference `backend/`. This confusion will cause divergence and makes it unclear which directory is authoritative.

**Fix:**
1. Delete `app/` entirely.
2. Update `docker-compose.yml` `api.build.context` from `./app` to `./backend`.
3. Update `worker.build.context` similarly.

---

### ARCH-05 🟡 Settings YAML Parser Ignores Most Config Sections

**File:** `backend/core/settings.py:94-120` (`from_yaml` method)

**Problem:** The `from_yaml` method manually extracts `redis.host` and `redis.port` from the YAML file but rebuilds `RedisConfig` with only those two fields. Other `RedisConfig` fields (e.g. `db`) are silently reset to defaults. The same applies to `CeleryConfig`, which only uses the reconstructed `redis_host`/`redis_port`, ignoring any `celery` section in the YAML.

**Fix:** Parse all sections from YAML uniformly:
```python
@classmethod
def from_yaml(cls, path: Path | str) -> "Settings":
    config_path = Path(path)
    if not config_path.exists():
        return cls()
    with open(config_path) as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return cls(**{k: v for k, v in data.items() if k in cls.model_fields})
```

---

### ARCH-06 🟡 Missing `__init__.py` in Several Packages

**File:** Various directories under `backend/`

Running `ruff check` with `INP001` (implicit namespace packages) flags 4 directories missing `__init__.py`. These should either have `__init__.py` added or be confirmed as namespace packages:

```bash
cd backend && uv run ruff check . --select INP001
```

---

## 5. Correctness Bugs

### BUG-01 🔴 `find_relationships` Silently Ignores `rel_type` Parameter

**File:** `backend/core/databases/neo4j_client.py:270-286`

**Problem:** (Also listed as SEC-05) The query `MATCH (p {name: $name})-[r:$rel_type]->(target)` is invalid Cypher — Neo4j does not support parameterizing relationship type labels using `$`. The query executes but silently treats `$rel_type` as a literal label name, which matches nothing. The `else` branch (all relationships) is effectively always used. This causes silently incorrect results when `rel_type` is provided.

**Reproduction:**
```python
client.find_relationships("Jeffrey Epstein", rel_type="FLEW_WITH")
# Returns ALL relationships, not just FLEW_WITH
```

**Fix:** See SEC-05 above — use an enum allowlist + safe string formatting.

---

### BUG-02 🔴 `process_document_task` Re-raises Celery-Retriable Exceptions After Logging Failure Status

**File:** `backend/workers/tasks.py:82-110`

**Problem:** When `OCRProcessingError` or `PDFProcessingError` is raised, the task:
1. Marks the file as `FAILED_PROCESSING` in the database.
2. Then re-raises the exception.

Because the task is decorated with `autoretry_for=(Exception,)`, Celery will retry it up to 3 times. Each retry will find the file already marked as `FAILED_PROCESSING`, attempt to process it again, fail, and update the database status again. The final database state is correct, but the intermediate retries are wasted, and the audit log will show multiple failure entries.

**Fix:** Either remove `autoretry_for` for processing errors and handle retries manually, or don't mark as `FAILED` until retries are exhausted:
```python
except OCRProcessingError as e:
    logger.error("OCR processing failed for file %s: %s", file_id, e)
    if self.request.retries >= self.max_retries:
        _update_file_status(file_id, ProcessingStatus.FAILED_OCR, str(e))
    raise  # let Celery retry
```

---

### BUG-03 🟠 `ProcessedDocumentSchema.validate_positive` Returns `None` for `character_count`

**File:** `backend/core/processing/schemas.py:57-64`

**Problem:** The `validate_positive` validator is applied to both `character_count` (non-optional `int`) and `page_count` (`int | None`). When the validator returns `None` for `character_count`, Pydantic accepts it (because the validator runs before type checking in `mode="before"`), resulting in `character_count = None` where `int` is expected. This causes a type error downstream when arithmetic is performed on `character_count`.

**Fix:** Split the validator:
```python
@field_validator("character_count", "word_count", mode="before")
@classmethod
def validate_non_negative_int(cls, v: Any) -> int:
    """Ensure count values are non-negative integers."""
    return max(0, int(v or 0))

@field_validator("page_count", mode="before")
@classmethod
def validate_optional_positive(cls, v: Any) -> int | None:
    """Ensure page_count is non-negative if provided."""
    if v is None:
        return None
    return max(0, int(v))
```

---

## 6. Code Quality Recommendations

### CQ-01 Replace All Logging f-Strings with `%`-Formatting

Applies to ~92 occurrences across the codebase. This is both a performance improvement (avoids string construction when the log level is disabled) and a best practice:

```python
# Before
logger.info(f"Connected to Neo4j: {self._settings.neo4j.uri}")

# After
logger.info("Connected to Neo4j: %s", self._settings.neo4j.uri)
```

### CQ-02 Replace `except Exception: pass/continue` with Logged Handlers

24 instances of `BLE001` (blind except). Each should either be narrowed to a specific exception type or log the error:

```python
# Before
except Exception:
    continue

# After
except (FileNotFoundError, json.JSONDecodeError) as exc:
    logger.debug("Skipping sidecar file: %s", exc)
    continue
```

### CQ-03 Move Imports Inside Functions to Top of Module

22 instances of `PLC0415` (imports inside functions). These pattern appears in `fact_extractor.py` and other agent files for lazy imports. While intentional for some cases (circular import avoidance), most should be moved to the module top level.

### CQ-04 Add Missing Public Docstrings

The following types of symbols are missing docstrings (65+ instances):
- Public classes without docstrings (`D101`)
- Public methods without docstrings (`D102`)
- `__init__` methods without docstrings (`D107`)
- Module-level docstrings (`D100`, `D104`)

### CQ-05 Use `logger.exception()` Inside Except Blocks

21 instances of `TRY400` — using `logger.error()` inside `except` blocks loses the traceback. Use `logger.exception()` to automatically attach the current exception:

```python
# Before
except Exception as e:
    logger.error(f"Failed: {e}")

# After
except Exception:
    logger.exception("Failed processing file %s", file_id)
```

### CQ-06 Async Functions Should Not Use Blocking I/O

9 instances of `ASYNC240` — async functions calling blocking `Path` methods or `open()`. In async contexts, use `anyio.Path` or `asyncio.to_thread`:

```python
# Before (blocks event loop)
async def save_json_sidecar(path: Path, doc: ProcessedDocumentSchema) -> Path:
    with open(path, "w") as f:
        f.write(doc.model_dump_json())

# After
import asyncio
async def save_json_sidecar(path: Path, doc: ProcessedDocumentSchema) -> Path:
    content = doc.model_dump_json()
    await asyncio.to_thread(path.write_text, content, encoding="utf-8")
    return path
```

### CQ-07 Boolean Arguments in Function Signatures

7 instances of `FBT001`/`FBT002` — boolean positional parameters. Replace with keyword-only arguments:

```python
# Before
def route_file(file_path: Path, ..., force_ocr: bool = False) -> ProcessingRoute:

# After
def route_file(file_path: Path, ..., *, force_ocr: bool = False) -> ProcessingRoute:
```

### CQ-08 Remove Duplicate `pydantic-settings` Dependency

**File:** `backend/pyproject.toml:16,28`

`pydantic-settings>=2.1.0` appears twice in the `dependencies` list. Remove the duplicate.

---

## 7. Test Coverage Gaps

The test suite requires 85% coverage (configured in `pyproject.toml`). The following high-risk areas lack tests:

### TC-01 Agent Pipeline (`backend/agents/`)

`fact_extractor.py`, `model_router.py`, and `mcp_tools.py` have minimal or no tests. The `FactExtractor`, `LinkAnalyst`, and `GraphArchitect` classes are core to the system but are not exercised in `tests/test_agents.py` beyond the alignment test.

**Required tests:**
- `test_fact_extractor_extracts_person_from_sidecar` — mock CrewAI + sidecar, assert entity output
- `test_model_router_falls_back_to_ollama_when_openrouter_unavailable`
- `test_mcp_tools_read_sidecar_raises_on_path_traversal` (validates SEC-06 fix)

### TC-02 API Endpoints (`backend/api/`)

`tests/` has no test file for `backend/api/__init__.py` or `backend/api/main.py`. The graph endpoints have zero test coverage.

**Required tests:**
- `test_get_network_graph_returns_nodes_and_links` — mock Neo4jClient, assert response schema
- `test_get_node_details_404_on_missing_node`
- `test_health_endpoint_returns_200`
- `test_api_key_required_when_configured` (validates SEC-03 fix)

### TC-03 Worker Task Retry Behavior (`backend/workers/tasks.py`)

The retry logic in `process_document_task` is not tested. In particular:
- Failure status should not be set until all retries are exhausted (BUG-02 fix)
- Files not in the ledger should return error dict without raising

**Required tests:**
- `test_process_document_task_marks_failed_after_max_retries`
- `test_process_document_task_returns_error_dict_for_missing_file`

### TC-04 Settings Loading (`backend/core/settings.py`)

The `from_yaml` method is complex and partially incorrect (ARCH-05). It has no dedicated tests.

**Required tests:**
- `test_settings_from_yaml_loads_redis_host`
- `test_settings_from_yaml_falls_back_to_defaults_when_file_missing`
- `test_settings_env_overrides_yaml`

---

## 8. AI Agent Task List

The following is a structured, ordered task list for an AI coding agent. Each task is self-contained with acceptance criteria.

---

### TASK-01: Fix All Auto-fixable Ruff Linting Errors

**Priority:** High  
**Effort:** Low (single command)

**Instructions:**
```
Run the following command from the backend/ directory:
  uv run ruff check . --fix

Then run:
  uv run ruff check .

Verify that the remaining error count is reduced to only manual-fix issues.
Commit the changes with message: "fix: auto-fix 61 ruff linting errors"
```

**Acceptance Criteria:**
- `ruff check .` reports ≤ 10 errors (only manual-fix categories)
- No test regressions

---

### TASK-02: Fix CORS Wildcard Configuration

**Priority:** Critical  
**Effort:** Low

**Instructions:**
```
File: backend/api/main.py

1. Add an import for `os` at the top of the file.
2. Before the app.add_middleware call, add:
   ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
3. Replace the CORSMiddleware instantiation:
   - Change allow_origins=["*"] to allow_origins=ALLOWED_ORIGINS
   - Change allow_methods=["*"] to allow_methods=["GET", "POST", "PUT", "DELETE"]

File: app/api/main.py (same fix if app/ is not deleted)

File: docker-compose.yml
   Add to the api service environment section:
   - ALLOWED_ORIGINS=http://localhost:3000

File: .env.example
   Add line: ALLOWED_ORIGINS=http://localhost:3000
```

**Acceptance Criteria:**
- `allow_origins` is never `["*"]`
- CORS origins are configurable via environment variable
- Existing health endpoint still works

---

### TASK-03: Remove Hardcoded Passwords from Version-Controlled Files

**Priority:** Critical  
**Effort:** Medium

**Instructions:**
```
1. File: backend/config.yaml
   Change:
     neo4j:
       password: "password"
   To:
     neo4j:
       password: ""   # set via EPSTEIN_NEO4J__PASSWORD env var

2. File: docker-compose.yml
   Change NEO4J_AUTH line:
     - NEO4J_AUTH=neo4j/password
   To:
     - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-changeme}

   Change all occurrences of:
     - NEO4J_PASSWORD=password
   To:
     - NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}

   Change cypher-shell healthcheck:
     cypher-shell -u neo4j -p password 'RETURN 1'
   To:
     cypher-shell -u neo4j -p ${NEO4J_PASSWORD:-changeme} 'RETURN 1'

3. File: .env.example
   Ensure it contains:
     NEO4J_PASSWORD=your_strong_password_here

4. File: .env (create if it doesn't exist, ensure it's in .gitignore)
   NEO4J_PASSWORD=changeme_for_local_dev
```

**Acceptance Criteria:**
- `grep -r "password" backend/config.yaml` returns no literal credential values
- `grep -r '"password"' docker-compose.yml` returns no results
- `.env` is in `.gitignore`

---

### TASK-04: Fix Cypher `find_relationships` Bug (SEC-05 / BUG-01)

**Priority:** Critical  
**Effort:** Low

**Instructions:**
```
File: backend/core/databases/neo4j_client.py

Find the find_relationships method (around line 263).

Replace the entire method with:

def find_relationships(
    self,
    entity_name: str,
    rel_type: str | None = None,
) -> list[dict[str, Any]]:
    """Find all relationships for an entity.
    
    Args:
        entity_name: Name of the entity to search.
        rel_type: Optional relationship type filter. Must be a valid
            RelationshipType value to prevent injection.
    
    Returns:
        List of relationship records.
    """
    from backend.core.schemas import RelationshipType
    
    if rel_type is not None:
        # Validate rel_type against the allowlist enum before embedding in query
        valid_types = {rt.value for rt in RelationshipType}
        if rel_type not in valid_types:
            raise ValueError(
                f"Invalid relationship type: {rel_type!r}. "
                f"Must be one of: {sorted(valid_types)}"
            )
        # Relationship type labels cannot be parameterized in Cypher;
        # embedding is safe because rel_type is validated against the enum allowlist.
        cypher = f"""
        MATCH (p {{name: $name}})-[r:{rel_type}]->(target)
        RETURN p, r, target
        """
    else:
        cypher = """
        MATCH (p {name: $name})-[r]->(target)
        RETURN p, r, target
        """
    
    return self.execute_query(cypher, {"name": entity_name})
```

**Acceptance Criteria:**
- `find_relationships("X", rel_type="FLEW_WITH")` returns only FLEW_WITH relationships
- `find_relationships("X", rel_type="INVALID")` raises `ValueError`
- Unit test added in `tests/test_databases.py`

---

### TASK-05: Fix ProcessedDocumentSchema Validator Bug (BUG-03)

**Priority:** High  
**Effort:** Low

**Instructions:**
```
File: backend/core/processing/schemas.py

Find the validate_positive field_validator (around line 57).

Replace:
    @field_validator("character_count", "page_count", mode="before")
    @classmethod
    def validate_positive(cls, v: Any) -> int | None:
        """Ensure values are non-negative."""
        if v is None:
            return None
        return max(0, int(v))

With:
    @field_validator("character_count", "word_count", mode="before")
    @classmethod
    def validate_non_negative_int(cls, v: Any) -> int:
        """Ensure count values are non-negative integers."""
        return max(0, int(v or 0))

    @field_validator("page_count", mode="before")
    @classmethod
    def validate_optional_non_negative(cls, v: Any) -> int | None:
        """Ensure page_count is non-negative if provided."""
        if v is None:
            return None
        return max(0, int(v))
```

**Acceptance Criteria:**
- `ProcessedDocumentSchema(character_count=None, ...)` raises `ValidationError`
- `ProcessedDocumentSchema(character_count=-5, ...)` sets `character_count=0`
- `ProcessedDocumentSchema(page_count=None, ...)` succeeds with `page_count=None`

---

### TASK-06: Add API Key Authentication

**Priority:** High  
**Effort:** Medium

**Instructions:**
```
1. Create new file: backend/api/auth.py with contents:

"""API key authentication dependency."""
import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_API_KEY_HEADER)) -> str:
    """Validate X-API-Key header when API_KEY environment variable is set.

    Args:
        api_key: Value from X-API-Key request header.

    Returns:
        The validated API key string.

    Raises:
        HTTPException: 403 if API_KEY is configured and key is invalid.
    """
    expected = os.environ.get("API_KEY", "")
    if not expected:
        return "unauthenticated"  # auth disabled when API_KEY not configured
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
    return api_key


2. File: backend/api/__init__.py
   Add import at top:
   from fastapi import Depends
   from backend.api.auth import require_api_key

   Add dependency to all route decorators:
   @router.get("/network", response_model=NetworkGraphResponse, dependencies=[Depends(require_api_key)])
   @router.get("/node/{node_name}", dependencies=[Depends(require_api_key)])
   @router.get("/stats", dependencies=[Depends(require_api_key)])

3. File: .env.example
   Add line:
   API_KEY=your_secret_api_key_here

4. File: docker-compose.yml
   Add to api service environment:
   - API_KEY=${API_KEY:-}
```

**Acceptance Criteria:**
- With `API_KEY` set, requests without `X-API-Key` return HTTP 403
- With `API_KEY` set, correct key returns HTTP 200
- Without `API_KEY` set, all requests pass through (backward compatible)
- Unit test added in `tests/test_api.py`

---

### TASK-07: Delete `app/` Directory and Fix Docker Build Context

**Priority:** High  
**Effort:** Low

**Instructions:**
```
1. Delete the entire app/ directory:
   rm -rf app/

2. File: docker-compose.yml
   Find the api service build section:
     build:
       context: ./app
       dockerfile: Dockerfile
   Change to:
     build:
       context: ./backend
       dockerfile: Dockerfile

   Find the worker service build section (same pattern):
     build:
       context: ./app
       dockerfile: Dockerfile.worker
   Change to:
     build:
       context: ./backend
       dockerfile: Dockerfile.worker

3. Verify the backend/ Dockerfile and Dockerfile.worker exist and are correct.
   The Dockerfile should COPY . /app and set WORKDIR /app.
```

**Acceptance Criteria:**
- `app/` directory no longer exists in the repository
- `docker-compose.yml` references `./backend` for all builds
- `docker compose build` succeeds (or at minimum, docker-compose.yml has no references to `./app`)

---

### TASK-08: Fix Celery Module-Level Settings Initialization

**Priority:** High  
**Effort:** Low

**Instructions:**
```
File: backend/workers/celery_app.py

Replace the entire file with:

"""
Celery application configuration.

Settings are applied lazily after configuration to ensure environment
variables from Docker are available before connecting to Redis.
"""

import logging

from celery import Celery

logger = logging.getLogger(__name__)


celery_app = Celery("epstein_osint")


@celery_app.on_after_configure.connect
def _apply_settings(sender: Celery, **kwargs: object) -> None:
    """Apply settings after Celery is configured (lazy initialization)."""
    from backend.core.settings import get_settings

    settings = get_settings()
    sender.conf.update(
        broker_url=settings.celery.broker_url,
        result_backend=settings.celery.result_backend,
        include=["backend.workers.tasks"],
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
        task_soft_time_limit=3000,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
    )
    logger.info("Celery configured with broker: %s", settings.celery.broker_url)
```

**Acceptance Criteria:**
- `from backend.workers.celery_app import celery_app` does not call `get_settings()`
- Settings are applied when Celery starts
- Existing tasks continue to work

---

### TASK-09: Fix `find_relationships` — Already Covered in TASK-04

*(Merged with TASK-04.)*

---

### TASK-10: Fix Celery Retry Logic for Processing Failures (BUG-02)

**Priority:** High  
**Effort:** Medium

**Instructions:**
```
File: backend/workers/tasks.py

In the process_document_task function, replace the exception handler blocks:

    except OCRProcessingError as e:
        logger.error(f"OCR processing failed for file {file_id}: {e}")
        _update_file_status(file_id, ProcessingStatus.FAILED_OCR, str(e))
        raise

    except PDFProcessingError as e:
        logger.error(f"PDF processing failed for file {file_id}: {e}")
        _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise

With:

    except OCRProcessingError as e:
        logger.exception("OCR processing failed for file %s", file_id)
        if self.request.retries >= self.max_retries:
            _update_file_status(file_id, ProcessingStatus.FAILED_OCR, str(e))
        raise self.retry(exc=e)

    except PDFProcessingError as e:
        logger.exception("PDF processing failed for file %s", file_id)
        if self.request.retries >= self.max_retries:
            _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise self.retry(exc=e)

    except ProcessingError as e:
        logger.exception("Processing failed for file %s", file_id)
        if self.request.retries >= self.max_retries:
            _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise self.retry(exc=e)

    except Exception as e:
        logger.exception("Unexpected error processing file %s", file_id)
        if self.request.retries >= self.max_retries:
            _update_file_status(file_id, ProcessingStatus.FAILED_PROCESSING, str(e))
        raise self.retry(exc=e)

Also remove autoretry_for from the decorator since we now handle retries manually:

@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    name="epstein.process_document",
)
```

**Acceptance Criteria:**
- File is only marked `FAILED` after all retries are exhausted
- Test: `test_process_document_task_marks_failed_after_max_retries`

---

### TASK-11: Fix DatabaseConnectionError to Scrub Credentials from Logs

**Priority:** High  
**Effort:** Low

**Instructions:**
```
File: backend/core/exceptions.py

Find DatabaseConnectionError.__init__ (around line 199).

Replace the body with:

    def __init__(
        self,
        database_type: str,
        connection_string: str,
        original_exception: Exception | None = None,
    ) -> None:
        from urllib.parse import urlparse, urlunparse
        self.database_type = database_type
        try:
            parsed = urlparse(connection_string)
            # Remove userinfo (credentials) from the URL before logging
            safe = parsed._replace(netloc=parsed.hostname or "")
            safe_url = urlunparse(safe)
        except Exception:
            safe_url = "<connection string redacted>"
        self.connection_string = safe_url
        super().__init__(
            message=f"Failed to connect to {database_type} database",
            details={"database_type": database_type, "connection_string": safe_url},
            original_exception=original_exception,
        )
```

**Acceptance Criteria:**
- `DatabaseConnectionError("neo4j", "bolt://neo4j:password@host:7687").connection_string` does not contain "password"
- Unit test added to `tests/test_exceptions.py`

---

### TASK-12: Add Tests for API Endpoints

**Priority:** High  
**Effort:** Medium

**Instructions:**
```
Create new file: tests/test_api.py

The file should use FastAPI's TestClient and mock the Neo4jClient.
Include tests for:
1. GET /health → 200 {"status": "healthy"}
2. GET /api/graph/stats → 200 dict with entity counts (mock Neo4jClient.get_graph_stats)
3. GET /api/graph/network → 200 NetworkGraphResponse (mock Neo4jClient.get_network_graph)
4. GET /api/graph/node/TestPerson → 200 dict (mock Neo4jClient.get_node_details)
5. GET /api/graph/node/MissingPerson → 404 (mock returns empty/None)
6. With API_KEY set: GET /api/graph/stats without header → 403
7. With API_KEY set: GET /api/graph/stats with correct header → 200

Use pytest-mock to patch backend.api.get_neo4j.
Use fastapi.testclient.TestClient(app) for requests.
Do not start the lifespan (use app with lifespan=None or mock the startup checks).
```

**Acceptance Criteria:**
- All 7 test cases pass
- Coverage for `backend/api/__init__.py` > 80%

---

### TASK-13: Remove Duplicate `pydantic-settings` Dependency

**Priority:** Low  
**Effort:** Trivial

**Instructions:**
```
File: backend/pyproject.toml

In the [project] dependencies list, remove the duplicate entry:
    "pydantic-settings>=2.1.0",

Only one occurrence should remain (line 16 is the original; line 28 is the duplicate).

Then run:
    cd backend && uv lock && uv sync
```

**Acceptance Criteria:**
- `grep "pydantic-settings" backend/pyproject.toml` returns exactly one line

---

### TASK-14: Fix Settings YAML Parser to Load All Config Sections Correctly

**Priority:** Medium  
**Effort:** Medium

**Instructions:**
```
File: backend/core/settings.py

Replace the entire from_yaml classmethod with:

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Settings":
        """Load settings from YAML file, with environment variable overrides.

        Environment variables take precedence over YAML values.
        Uses the EPSTEIN_ prefix and __ as nested delimiter (pydantic-settings).

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Settings instance with merged config.
        """
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        # Build nested config models from YAML sections
        # pydantic-settings env vars will automatically override these values
        init_kwargs: dict[str, Any] = {}
        field_classes = {
            "app": AppConfig,
            "storage": StorageConfig,
            "database": DatabaseConfig,
            "redis": RedisConfig,
            "celery": CeleryConfig,
            "chromadb": ChromaDBConfig,
            "neo4j": Neo4jConfig,
            "ollama": OllamaConfig,
            "openrouter": OpenRouterConfig,
            "downloader": DownloaderConfig,
            "ocr": OCRConfig,
            "vectorization": VectorizationConfig,
            "websocket": WebSocketConfig,
        }
        for key, model_cls in field_classes.items():
            if key in data:
                init_kwargs[key] = model_cls(**data[key])

        return cls(**init_kwargs)
```

**Acceptance Criteria:**
- `Settings.from_yaml("config.yaml").redis.db` correctly reflects the YAML value (not always 0)
- `Settings.from_yaml("config.yaml").celery.broker_url` reflects the YAML celery section
- Tests in `tests/test_settings.py` (new file) verify these

---

### TASK-15: Fix Path Traversal in `MCPTools.read_sidecar`

**Priority:** High  
**Effort:** Low

**Instructions:**
```
File: backend/agents/mcp_tools.py

Find the read_sidecar method.

Add path validation at the beginning of the method:

    def read_sidecar(self, file_id: int, data_dir: str | None = None) -> dict[str, Any]:
        """Read a processed JSON sidecar file.
        ...
        """
        base = Path(data_dir or str(self._settings.storage.data_dir)).resolve()
        search_path = (base / "processed").resolve()

        # Prevent path traversal outside of the configured data directory
        if not str(search_path).startswith(str(base)):
            raise ValueError(
                f"Resolved sidecar path {search_path} is outside the allowed "
                f"data directory {base}"
            )

        # rest of existing method using search_path ...
```

**Acceptance Criteria:**
- `read_sidecar(1, data_dir="../../etc")` raises `ValueError`
- `read_sidecar(1)` works normally with valid data directory
- Test added to `tests/test_agents.py`

---

## Quick Reference: Files by Priority

### Fix Immediately (Security / Breaking Bugs)

| File | Issue | Task |
|---|---|---|
| `backend/api/main.py` | Wildcard CORS | TASK-02 |
| `backend/config.yaml` | Hardcoded password | TASK-03 |
| `docker-compose.yml` | Hardcoded password | TASK-03 |
| `backend/core/databases/neo4j_client.py` | Cypher rel_type bug | TASK-04 |
| `backend/core/processing/schemas.py` | Validator returns None for int | TASK-05 |
| `backend/workers/tasks.py` | Celery retry marks FAILED too early | TASK-10 |
| `backend/agents/mcp_tools.py` | Path traversal in read_sidecar | TASK-15 |

### Fix Soon (Linting / Architecture)

| File | Issue | Task |
|---|---|---|
| All Python files in `backend/` | 61 auto-fixable linting errors | TASK-01 |
| `backend/workers/celery_app.py` | Module-level settings init | TASK-08 |
| `backend/core/exceptions.py` | Credential leak in logs | TASK-11 |
| `backend/core/settings.py` | YAML parser ignores most sections | TASK-14 |
| `app/` directory | Duplicate of backend/ | TASK-07 |
| `backend/pyproject.toml` | Duplicate dependency | TASK-13 |

### Fix When Possible (Quality / Coverage)

| File | Issue | Task |
|---|---|---|
| `tests/` | No API endpoint tests | TASK-12 |
| `backend/api/auth.py` (new) | Missing authentication | TASK-06 |

---

*This document was generated by automated analysis of the repository at commit `022daa6`. All code suggestions should be reviewed and tested before merging.*
