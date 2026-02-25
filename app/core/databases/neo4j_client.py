"""
Neo4j client for knowledge graph operations.

Provides parameterized Cypher queries for entity and relationship management.
"""

import logging
from typing import Any

from neo4j import GraphDatabase

from backend.core.exceptions import DatabaseConnectionError, DatabaseQueryError
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j client with parameterized Cypher queries.

    All queries use parameterization to prevent Cypher injection.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver = None

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self._settings.neo4j.uri,
                    auth=(
                        self._settings.neo4j.username,
                        self._settings.neo4j.password,
                    ),
                )
                logger.info(f"Connected to Neo4j: {self._settings.neo4j.uri}")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise DatabaseConnectionError(
                    database_type="neo4j",
                    connection_string=self._settings.neo4j.uri,
                    original_exception=e,
                ) from e
        return self._driver

    def close(self) -> None:
        """Close the driver."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def execute_query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query with parameters.

        Args:
            cypher: Cypher query string.
            parameters: Query parameters.

        Returns:
            List of result records.

        Raises:
            DatabaseQueryError: If query fails.
        """
        driver = self._get_driver()

        try:
            with driver.session(database=self._settings.neo4j.database) as session:
                result = session.run(cypher, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Neo4j query failed: {e}")
            raise DatabaseQueryError(
                query=cypher[:100],
                reason=str(e),
            ) from e

    def merge_person(
        self,
        name: str,
        aliases: list[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge a Person node.

        Args:
            name: Person's full name.
            aliases: List of aliases.
            properties: Additional properties.

        Returns:
            Created/merged node data.
        """
        params = {
            "name": name,
            "aliases": aliases or [],
            **(properties or {}),
        }

        cypher = """
        MERGE (p:Person {name: $name})
        SET p.aliases = $aliases,
            p.updated_at = datetime()
        WITH p
        SET p += $properties
        RETURN p
        """

        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def merge_organization(
        self,
        name: str,
        organization_type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge an Organization node."""
        params = {
            "name": name,
            "organization_type": organization_type,
            **(properties or {}),
        }

        cypher = """
        MERGE (o:Organization {name: $name})
        SET o.organization_type = $organization_type,
            o.updated_at = datetime()
        WITH o
        SET o += $properties
        RETURN o
        """

        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def merge_location(
        self,
        name: str,
        location_type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge a Location node."""
        params = {
            "name": name,
            "location_type": location_type,
            **(properties or {}),
        }

        cypher = """
        MERGE (l:Location {name: $name})
        SET l.location_type = $location_type,
            l.updated_at = datetime()
        WITH l
        SET l += $properties
        RETURN l
        """

        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def merge_aircraft(
        self,
        tail_number: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge an Aircraft node."""
        params = {
            "tail_number": tail_number.upper(),
            **(properties or {}),
        }

        cypher = """
        MERGE (a:Aircraft {tail_number: $tail_number})
        SET a.updated_at = datetime()
        WITH a
        SET a += $properties
        RETURN a
        """

        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def merge_event(
        self,
        event_id: str,
        event_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge an Event node."""
        params = {
            "event_id": event_id,
            "event_type": event_type,
            **(properties or {}),
        }

        cypher = """
        MERGE (e:Event {event_id: $event_id})
        SET e.event_type = $event_type,
            e.updated_at = datetime()
        WITH e
        SET e += $properties
        RETURN e
        """

        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def create_relationship(
        self,
        from_name: str,
        from_label: str,
        to_name: str,
        to_label: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between two nodes.

        This is the key method for the "Depth Matrix" - it accepts
        a relationship type and properties (including the 1-10 score).

        Args:
            from_name: Name of source node.
            from_label: Label of source node (Person, Organization, etc.).
            to_name: Name of target node.
            to_label: Label of target node.
            rel_type: Relationship type (e.g., "FLEW_WITH", "MET_AT").
            properties: Relationship properties (score, evidence, dates, etc.).

        Returns:
            Created relationship data.
        """
        params = {
            "from_name": from_name,
            "from_label": from_label,
            "to_name": to_name,
            "to_label": to_label,
            "rel_type": rel_type,
            "properties": properties or {},
        }

        cypher = """
        MATCH (from_node:$from_label {name: $from_name})
        MATCH (to_node:$to_label {name: $to_name})
        MERGE (from_node)-[r:$rel_type]->(to_node)
        SET r = $properties,
            r.created_at = datetime()
        RETURN from_node, r, to_node
        """

        result = self.execute_query(cypher, params)
        return result[0] if result else {}

    def find_person(self, name: str) -> list[dict[str, Any]]:
        """Find a person by name."""
        return self.execute_query(
            "MATCH (p:Person {name: $name}) RETURN p",
            {"name": name},
        )

    def find_relationships(
        self,
        entity_name: str,
        rel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find all relationships for an entity."""
        if rel_type:
            cypher = """
            MATCH (p {name: $name})-[r:$rel_type]->(target)
            RETURN p, r, target
            """
        else:
            cypher = """
            MATCH (p {name: $name})-[r]->(target)
            RETURN p, r, target
            """

        return self.execute_query(cypher, {"name": entity_name, "rel_type": rel_type})

    def get_graph_stats(self) -> dict[str, int]:
        """Get graph statistics."""
        cypher = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        """

        results = self.execute_query(cypher, {})

        stats = {}
        for row in results:
            stats[row["label"]] = row["count"]

        return stats

    def get_network_graph(
        self,
        limit: int = 500,
        min_score: int = 1,
    ) -> dict[str, Any]:
        """Get network graph data for visualization.

        Args:
            limit: Maximum number of nodes to return.
            min_score: Minimum relationship score to include.

        Returns:
            Dictionary with 'nodes' and 'links' arrays.
        """
        cypher = """
        MATCH (n)-[r]->(m)
        WHERE r.score >= $min_score
        WITH n, m, r
        ORDER BY r.score DESC
        LIMIT $limit
        RETURN 
            collect(DISTINCT {id: id(n), label: labels(n)[0], name: COALESCE(n.name, n.tail_number, n.event_id)}) as nodes,
            collect(DISTINCT {source: id(n), target: id(m), type: type(r), depth_score: COALESCE(r.score, 1)}) as links
        """

        results = self.execute_query(cypher, {"limit": limit, "min_score": min_score})

        if not results:
            return {"nodes": [], "links": []}

        raw = results[0]

        node_map: dict[int, dict[str, Any]] = {}
        for node in raw.get("nodes", []):
            node_map[node["id"]] = node

        return {
            "nodes": list(node_map.values()),
            "links": raw.get("links", []),
        }

    def get_node_details(self, node_name: str) -> dict[str, Any]:
        """Get detailed information about a node.

        Args:
            node_name: Name of the node.

        Returns:
            Node details with relationships.
        """
        cypher = """
        MATCH (n {name: $name})-[r]->(m)
        RETURN n, collect({target: m.name, type: type(r), score: COALESCE(r.score, 1), evidence: COALESCE(r.evidence, [])}) as outgoing
        """

        results = self.execute_query(cypher, {"name": node_name})

        if not results:
            cypher = """
            MATCH (n)-[r]->(m {name: $name})
            RETURN n, collect({target: m.name, type: type(r), score: COALESCE(r.score, 1), evidence: COALESCE(r.evidence, [])}) as incoming
            """
            results = self.execute_query(cypher, {"name": node_name})

        if not results:
            return {}

        return results[0]
