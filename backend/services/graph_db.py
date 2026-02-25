import logging
from typing import Any

from neo4j import GraphDatabase

from backend.core.interfaces import GraphDBBase, GraphDBProtocol
from backend.core.settings import Settings

logger = logging.getLogger(__name__)


class Neo4jClient(GraphDBBase):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver = GraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.username, settings.neo4j.password),
        )

    def execute_query(
        self, cypher: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        with self._driver.session(database=self._settings.neo4j.database) as session:
            result = session.run(cypher, parameters or {})
            return [dict(record) for record in result]

    def create_node(self, label: str, properties: dict[str, Any]) -> None:
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        cypher = f"CREATE (n:{label} {{{props_str}}})"
        self.execute_query(cypher, properties)
        logger.info(f"Created node: {label} with props: {properties}")

    def create_relationship(
        self,
        from_node: str,
        to_node: str,
        rel_type: str,
        properties: dict[str, Any],
    ) -> None:
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        cypher = f"""
        MATCH (a {{name: $from_name}})
        MATCH (b {{name: $to_name}})
        CREATE (a)-[r:{rel_type} {{{props_str}}}]->(b)
        """
        params = {**properties, "from_name": from_node, "to_name": to_node}
        self.execute_query(cypher, params)
        logger.info(f"Created relationship: {from_node}-[:{rel_type}]->{to_node}")

    def get_node(self, label: str, property_key: str, property_value: Any) -> dict[str, Any] | None:
        cypher = f"MATCH (n:{label} {{{property_key}: $value}}) RETURN n"
        result = self.execute_query(cypher, {"value": property_value})
        return result[0].get("n") if result else None

    def find_relationships(
        self,
        from_node: str | None = None,
        to_node: str | None = None,
        rel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        cypher = "MATCH (a)-[r"
        if rel_type:
            cypher += f":{rel_type}"
        cypher += "]->(b)"

        conditions = []
        if from_node:
            conditions.append("a.name = $from_node")
        if to_node:
            conditions.append("b.name = $to_node")

        if conditions:
            cypher += " WHERE " + " AND ".join(conditions)

        cypher += " RETURN a, r, b"

        params = {}
        if from_node:
            params["from_node"] = from_node
        if to_node:
            params["to_node"] = to_node

        return self.execute_query(cypher, params)

    def close(self) -> None:
        self._driver.close()
