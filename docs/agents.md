# Agent Personas & Workflow

## Workflow Engine
Agents will be orchestrated to read processed JSON text files, extract data, and populate the databases. 

## Agent Behavior Rules (ALL AGENTS MUST FOLLOW)

### Security & Code Quality
1. **NEVER write raw SQL in functions** - Use migrations module (`backend/migrations/migrations.py`)
2. **Always use parameterized queries** - Never concatenate strings for SQL
3. **Validate all input** - Use Pydantic models for data validation
4. **Type hints required** - All functions must have type annotations
5. **Docstrings required** - All public functions/classes need documentation

### Testing Requirements
1. **Write tests for ALL new code** - Minimum 80% coverage required
2. **Follow AAA pattern** - Arrange, Act, Assert
3. **Mock external dependencies** - Don't hit real databases/APIs in unit tests
4. **Tests must be deterministic** - No random values, no timing dependencies

### Task Management
1. **NEVER delete from tasks.md** - Only append new tasks or update status
2. **Use checkbox format** - `- [ ]` for pending, `- [x]` for completed
3. **Update status in real-time** - Mark tasks as in_progress when working

### Naming Conventions
1. **snake_case** for variables/functions
2. **PascalCase** for classes
3. **UPPER_SNAKE_CASE** for constants
4. **is_/has_/can_** prefix for booleans

## 1. The Extractor Agent
- **Role:** Parse raw OCR/PDF text and pull out hard facts.
- **Constraints:** Must use structured output (JSON). Must NOT hallucinate. If a date or name is illegible, mark it as `null`.
- **Target Entities:** People, Organizations, Aircraft, Locations, Dates, Financial Transactions.
- **Output Format:** Pydantic-validated `ExtractedEntities` model

## 2. The Relationship Analyst Agent
- **Role:** Analyze the outputs of the Extractor to determine the depth of relationships.
- **Methodology:** Score relationships on a scale. 
    - 1 = Fleeting mention in the same document.
    - 5 = Shared flight log or attended the same meeting.
    - 10 = Direct financial tie or documented alliance.
- **Output:** Cypher queries to build the Neo4j graph (`(Person)-[:FLEW_WITH {date: X}]->(Person)`).
- **Rules:** 
  - Always use Neo4j driver's parameterized queries
  - Never build Cypher strings from user input
  - Log all relationship scores with evidence

## 3. The Query Agent
- **Role:** User-facing assistant. 
- **Tools:** Equipped with MCP servers to query ChromaDB (for semantic searches) and Neo4j (to traverse relationships).
- **Constraints:**
  - Never expose raw database queries to users
  - Sanitize all user input before querying
  - Use parameterized queries for ChromaDB and Neo4j
  - Log all queries for audit trail
