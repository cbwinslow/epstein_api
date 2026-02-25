"""
AI Agent implementations for OSINT analysis.

Three primary agents:
1. Fact Extractor - extracts entities from JSON sidecars
2. Link Analyst - determines relationship depth (1-10)
3. Graph Architect - creates Neo4j relationships

Integrated with CrewAI for multi-agent orchestration.
"""

import json
import logging
from pathlib import Path
from typing import Any

from crewai import Agent, Task, Crew, Process
from langchain_core.tools import tool

from backend.agents.model_router import ModelRouter
from backend.agents.mcp_tools import MCPTools
from backend.agents.telemetry import TelemetryLogger
from backend.core.exceptions import AgentParsingError
from backend.core.processing.sidecar import load_json_sidecar
from backend.core.schemas import ExtractedEntitiesOutput
from backend.core.settings import Settings

logger = logging.getLogger(__name__)

_mcp_tools_instance: MCPTools | None = None
_telemetry_instance: TelemetryLogger | None = None


def get_mcp_tools(settings: Settings) -> MCPTools:
    """Get or create MCP tools instance."""
    global _mcp_tools_instance
    if _mcp_tools_instance is None:
        _mcp_tools_instance = MCPTools(settings)
    return _mcp_tools_instance


def get_telemetry(settings: Settings) -> TelemetryLogger:
    """Get or create telemetry instance."""
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = TelemetryLogger(settings)
    return _telemetry_instance


@tool("read_sidecar")
def read_sidecar_tool(file_id: int) -> str:
    """Read a processed JSON sidecar file by file ID.

    Args:
        file_id: The file ID to read.

    Returns:
        Sidecar data as JSON string.
    """
    from backend.core.settings import get_settings

    settings = get_settings()
    tools = get_mcp_tools(settings)
    try:
        data = tools.read_sidecar(file_id)
        return json.dumps(data, indent=2)
    except FileNotFoundError as e:
        return f"Error: {str(e)}"


@tool("query_vector_db")
def query_vector_db_tool(query: str, n_results: int = 10) -> str:
    """Query the vector database for similar documents.

    Args:
        query: Search query text.
        n_results: Number of results (default 10).

    Returns:
        Matching documents as JSON string.
    """
    from backend.core.settings import get_settings

    settings = get_settings()
    tools = get_mcp_tools(settings)
    results = tools.query_vector_db(query, n_results=n_results)
    return json.dumps(results, indent=2)


@tool("search_graph")
def search_graph_tool(entity_name: str | None = None, cypher: str | None = None) -> str:
    """Search the knowledge graph for entities or run custom queries.

    Args:
        entity_name: Find relationships for entity.
        cypher: Custom Cypher query (expert mode).

    Returns:
        Query results as JSON string.
    """
    from backend.core.settings import get_settings

    settings = get_settings()
    tools = get_mcp_tools(settings)
    results = tools.search_graph(entity_name=entity_name, cypher=cypher)
    return json.dumps(results, indent=2)


class BaseAgent:
    """Base class for all agents."""

    def __init__(self, settings: Settings, model_router: ModelRouter) -> None:
        self._settings = settings
        self._router = model_router

    async def run(self, input_data: Any, **kwargs: Any) -> dict[str, Any]:
        """Run the agent. Must be implemented by subclasses."""
        raise NotImplementedError


class FactExtractor(BaseAgent):
    """Extracts entities from processed JSON sidecars.

    Uses the Methodology Rubric to identify:
    - PERSON: Names, aliases, titles
    - ORGANIZATION: Companies, foundations
    - LOCATION: Addresses, islands, properties
    - AIRCRAFT: Tail numbers
    - EVENT: Meetings, flights, transactions
    """

    EXTRACTION_PROMPT = """You are an expert OSINT analyst extracting entities from Epstein-related documents.

Your task is to extract structured entities from the provided text.
Follow the methodology exactly.

## Entity Types to Extract:

### PERSON
Full names, aliases, or titles (e.g., "Prince Andrew", "Doe 107", "Mr. Epstein")

### ORGANIZATION  
Companies, foundations, shell corporations, legal entities

### LOCATION
Specific addresses, islands, properties, flight destinations

### AIRCRAFT
Tail numbers (format: N##### or similar)

### EVENT
Meetings, flights, court depositions, financial transfers

## Rules:
1. ONLY extract entities that are explicitly mentioned in the text
2. If text is illegible or unclear, mark as null
3. Do NOT hallucinate or infer entities not in the text
4. Use "N/A" for missing information

## Output Format:
Return ONLY a JSON object with this structure:
{
  "persons": [{"full_name": "...", "aliases": [], "titles": [], "confidence": "high/medium/low"}],
  "organizations": [{"name": "...", "organization_type": "...", "confidence": "..."}],
  "aircraft": [{"tail_number": "...", "confidence": "..."}],
  "locations": [{"name": "...", "location_type": "...", "confidence": "..."}],
  "events": [{"event_type": "...", "participants": [...], "confidence": "..."}]
}

Now extract entities from this document:
{text}
"""

    async def run(self, sidecar_path: Path, **kwargs: Any) -> dict[str, Any]:
        """Extract entities from a processed sidecar file.

        Args:
            sidecar_path: Path to the JSON sidecar.

        Returns:
            Extracted entities dictionary.

        Raises:
            AgentParsingError: If extraction fails.
        """
        try:
            doc = load_json_sidecar(sidecar_path)

            prompt = self.EXTRACTION_PROMPT.format(text=doc.raw_text[:8000])

            schema = {
                "persons": [
                    {"full_name": "string", "aliases": [], "titles": [], "confidence": "string"}
                ],
                "organizations": [
                    {"name": "string", "organization_type": "string", "confidence": "string"}
                ],
                "aircraft": [{"tail_number": "string", "confidence": "string"}],
                "locations": [
                    {"name": "string", "location_type": "string", "confidence": "string"}
                ],
                "events": [{"event_type": "string", "participants": [], "confidence": "string"}],
            }

            result = await self._router.generate_structured(
                task_type="extract",
                prompt=prompt,
                schema=schema,
            )

            if "error" in result:
                raise AgentParsingError(
                    agent_name="FactExtractor",
                    raw_output=str(result),
                    validation_errors=[result.get("error", "Unknown error")],
                )

            result["source_file"] = str(sidecar_path)
            result["file_id"] = doc.original_file_id

            logger.info(f"Extracted entities from {sidecar_path.name}")

            return result

        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            raise AgentParsingError(
                agent_name="FactExtractor",
                raw_output="",
                validation_errors=[str(e)],
            ) from e


class LinkAnalyst(BaseAgent):
    """Analyzes relationships and assigns depth scores (1-10).

    Uses the Depth Matrix from methodology:
    - Level 1-2: Incidental (same document, no interaction)
    - Level 3-4: Proximity (same event, different dates)
    - Level 5-6: Direct Contact (documented meetings, same flight)
    - Level 7-8: Professional/Financial (board, transactions)
    - Level 9-10: Core Network (co-defendants, facilitators)
    """

    SCORING_PROMPT = """You are an expert relationship analyst for an OSINT investigation.

Your task is to analyze extracted entities and determine relationship depth.

## Depth Matrix (1-10 Scale):

### Level 1-2: Incidental
- Mentioned in same document but no direct interaction
- Address book entries without context
- Example: Both appear in same flight manifest but different dates

### Level 3-4: Proximity
- Attended same large event
- Flown on same aircraft but different dates
- Example: Both were on island at different times

### Level 5-6: Direct Contact
- Documented meetings
- Flown on same specific flight
- Direct email correspondence
- Example: Flight log shows both passengers on same date

### Level 7-8: Professional/Financial Ties
- Shared board memberships
- Direct financial transactions
- Legal representation
- Example: Donor/recipient of funds

### Level 9-10: Core Network
- Co-defendants
- Facilitators
- Shared ownership of shell companies
- Repeat, high-frequency travel together

## Analysis Task:
Given these entities and context, determine relationships and scores.

Entities:
{entities}

Context (from vector search):
{context}

## Output Format:
Return ONLY JSON:
{{
  "relationships": [
    {{
      "from_entity": "...",
      "to_entity": "...",
      "relationship_type": "FLEW_WITH/MET_AT/WORKED_FOR/etc",
      "score": 1-10,
      "evidence": ["..."],
      "confidence": "high/medium/low"
    }}
  ]
}}
"""

    async def run(
        self,
        entities: dict[str, Any],
        context_results: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Analyze relationships between entities.

        Args:
            entities: Extracted entities from FactExtractor.
            context_results: Optional context from vector search.

        Returns:
            Relationships with depth scores.
        """
        context = json.dumps(context_results or [])[:2000]
        entities_text = json.dumps(entities)[:3000]

        prompt = self.SCORING_PROMPT.format(
            entities=entities_text,
            context=context,
        )

        schema = {
            "relationships": [
                {
                    "from_entity": "string",
                    "to_entity": "string",
                    "relationship_type": "string",
                    "score": "number",
                    "evidence": [],
                    "confidence": "string",
                }
            ]
        }

        result = await self._router.generate_structured(
            task_type="score",
            prompt=prompt,
            schema=schema,
        )

        logger.info(f"Scored {len(result.get('relationships', []))} relationships")

        return result


class GraphArchitect(BaseAgent):
    """Converts relationships to Neo4j Cypher queries.

    Takes Link Analyst output and creates parameterized Cypher
    queries for the knowledge graph.
    """

    async def run(self, relationships: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        """Convert relationships to Neo4j operations.

        Args:
            relationships: Relationships from LinkAnalyst.

        Returns:
            List of Neo4j operation dicts.
        """
        operations = []

        for rel in relationships:
            from_entity = rel.get("from_entity", "")
            to_entity = rel.get("to_entity", "")
            rel_type = rel.get("relationship_type", "ASSOCIATED_WITH")
            score = rel.get("score", 1)

            if not from_entity or not to_entity:
                continue

            entity_type_from = self._infer_entity_type(from_entity)
            entity_type_to = self._infer_entity_type(to_entity)

            op = {
                "type": "merge_relationship",
                "from_name": from_entity,
                "from_label": entity_type_from,
                "to_name": to_entity,
                "to_label": entity_type_to,
                "rel_type": rel_type,
                "properties": {
                    "score": score,
                    "evidence": rel.get("evidence", []),
                    "confidence": rel.get("confidence", "medium"),
                },
            }

            operations.append(op)

        logger.info(f"Generated {len(operations)} Neo4j operations")

        return operations

    def _infer_entity_type(self, name: str) -> str:
        """Infer entity type from name pattern."""
        name_upper = name.upper()
        name_lower = name.lower()

        if name_upper.startswith("N") and any(c.isdigit() for c in name):
            return "Aircraft"

        if any(kw in name_lower for kw in ["island", "street", "ave", "mansion", "property"]):
            return "Location"

        if any(kw in name_lower for kw in ["inc", "llc", "corp", "trust", "foundation", "company"]):
            return "Organization"

        return "Person"


class AgentOrchestrator:
    """Orchestrates the full agent pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._router = ModelRouter(settings)
        self._fact_extractor = FactExtractor(settings, self._router)
        self._link_analyst = LinkAnalyst(settings, self._router)
        self._graph_architect = GraphArchitect(settings, self._router)

    async def analyze_document(
        self,
        sidecar_path: Path,
        context_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run full analysis pipeline.

        Args:
            sidecar_path: Path to processed sidecar.
            context_results: Optional context from vector DB.

        Returns:
            Complete analysis results.
        """
        entities = await self._fact_extractor.run(sidecar_path)

        relationships = await self._link_analyst.run(entities, context_results)

        neo4j_ops = await self._graph_architect.run(relationships.get("relationships", []))

        return {
            "entities": entities,
            "relationships": relationships,
            "neo4j_operations": neo4j_ops,
        }


class CrewAIOrchestrator:
    """CrewAI-based orchestration for the agent swarm."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._router = ModelRouter(settings)
        self._telemetry = get_telemetry(settings)
        self._crew: Crew | None = None

    def _create_agents(self) -> tuple[Agent, Agent, Agent]:
        """Create the CrewAI agents."""
        fact_extractor_agent = Agent(
            role="Fact Extractor",
            goal="Extract structured entities (PERSON, ORGANIZATION, LOCATION, AIRCRAFT, EVENT) from documents",
            backstory="""You are an expert OSINT analyst specializing in entity extraction.
                You follow strict methodology to only extract entities explicitly mentioned in text.
                Use the read_sidecar tool to access processed documents.""",
            tools=[read_sidecar_tool, query_vector_db_tool],
            verbose=True,
            allow_delegation=False,
        )

        link_analyst_agent = Agent(
            role="Link Analyst",
            goal="Analyze relationships between entities and assign depth scores (1-10)",
            backstory="""You are an expert relationship analyst.
                You use the Depth Matrix methodology:
                - Level 1-2: Incidental (same document, no interaction)
                - Level 3-4: Proximity (same event, different dates)
                - Level 5-6: Direct Contact (documented meetings, same flight)
                - Level 7-8: Professional/Financial (board, transactions)
                - Level 9-10: Core Network (co-defendants, facilitators)
                Use search_graph to check existing entities.""",
            tools=[search_graph_tool, query_vector_db_tool],
            verbose=True,
            allow_delegation=False,
        )

        graph_architect_agent = Agent(
            role="Graph Architect",
            goal="Convert relationships to Neo4j Cypher operations",
            backstory="""You are an expert at knowledge graph construction.
                You convert relationship analysis into parameterized Neo4j operations.
                Ensure proper entity types: Person, Organization, Location, Aircraft, Event.""",
            tools=[search_graph_tool],
            verbose=True,
            allow_delegation=False,
        )

        return fact_extractor_agent, link_analyst_agent, graph_architect_agent

    def _create_tasks(
        self,
        file_id: int,
        fact_agent: Agent,
        link_agent: Agent,
        graph_agent: Agent,
    ) -> tuple[Task, Task, Task]:
        """Create the CrewAI tasks."""
        extract_task = Task(
            description=f"Extract all entities from file_id {file_id}. "
            "Identify PERSON, ORGANIZATION, LOCATION, AIRCRAFT, and EVENT entities. "
            "Return structured JSON with confidence scores.",
            agent=fact_agent,
            expected_output="JSON with persons, organizations, locations, aircraft, events arrays",
        )

        score_task = Task(
            description="Analyze relationships between extracted entities. "
            "Query vector DB for additional context. "
            "Assign relationship scores 1-10 based on methodology.",
            agent=link_agent,
            context=[extract_task],
            expected_output="JSON with relationships array containing from_entity, to_entity, score, evidence",
        )

        graph_task = Task(
            description="Convert scored relationships to Neo4j operations. "
            "Infer entity types and create parameterized merge operations.",
            agent=graph_agent,
            context=[score_task],
            expected_output="JSON array of Neo4j operations with type, from_name, to_name, properties",
        )

        return extract_task, score_task, graph_task

    async def analyze_document(
        self,
        sidecar_path: Path,
        file_id: int,
    ) -> dict[str, Any]:
        """Run CrewAI analysis pipeline.

        Args:
            sidecar_path: Path to processed sidecar.
            file_id: File ID for the document.

        Returns:
            Complete analysis results from CrewAI.
        """
        self._telemetry.log(
            agent_name="CrewAIOrchestrator",
            input_file=str(sidecar_path),
            logic_reasoning="Starting CrewAI pipeline",
            status="started",
        )

        try:
            fact_agent, link_agent, graph_agent = self._create_agents()

            extract_task, score_task, graph_task = self._create_tasks(
                file_id, fact_agent, link_agent, graph_agent
            )

            self._crew = Crew(
                agents=[fact_agent, link_agent, graph_agent],
                tasks=[extract_task, score_task, graph_task],
                process=Process.sequential,
                verbose=True,
            )

            result = self._crew.kickoff(
                inputs={"file_id": file_id, "sidecar_path": str(sidecar_path)}
            )

            self._telemetry.log(
                agent_name="CrewAIOrchestrator",
                input_file=str(sidecar_path),
                logic_reasoning="CrewAI pipeline completed successfully",
                output_data={"result": str(result)},
                status="success",
            )

            return {
                "status": "success",
                "result": str(result),
                "file_id": file_id,
            }

        except Exception as e:
            logger.error(f"CrewAI analysis failed: {e}")
            self._telemetry.log(
                agent_name="CrewAIOrchestrator",
                input_file=str(sidecar_path),
                logic_reasoning=f"CrewAI pipeline failed: {str(e)}",
                status="error",
                error_message=str(e),
            )
            return {
                "status": "error",
                "error": str(e),
                "file_id": file_id,
            }

    async def run_with_telemetry(
        self,
        sidecar_path: Path,
        file_id: int,
    ) -> dict[str, Any]:
        """Run analysis with full telemetry logging.

        Args:
            sidecar_path: Path to processed sidecar.
            file_id: File ID for the document.

        Returns:
            Complete analysis results with telemetry.
        """
        result = await self.analyze_document(sidecar_path, file_id)

        failed_ops = self._telemetry.get_failed_operations(limit=10)

        return {
            **result,
            "telemetry": {
                "recent_failures": failed_ops,
            },
        }
