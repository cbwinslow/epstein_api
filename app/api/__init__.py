"""
FastAPI routes for graph API endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from backend.core.databases.neo4j_client import Neo4jClient
from backend.core.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])

_neo4j_client: Neo4jClient | None = None


def get_neo4j() -> Neo4jClient:
    global _neo4j_client
    if _neo4j_client is None:
        settings = get_settings()
        _neo4j_client = Neo4jClient(settings)
    return _neo4j_client


class NetworkGraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    links: list[dict[str, Any]]


@router.get("/network", response_model=NetworkGraphResponse)
async def get_network_graph(
    limit: int = Query(default=500, ge=10, le=2000),
    min_score: int = Query(default=1, ge=1, le=10),
) -> NetworkGraphResponse:
    """Get network graph data for visualization.

    Returns nodes and links formatted for react-force-graph.
    - Nodes: {id, label, name}
    - Links: {source, target, type, depth_score}
    """
    try:
        client = get_neo4j()
        data = client.get_network_graph(limit=limit, min_score=min_score)
        return NetworkGraphResponse(**data)
    except Exception as e:
        logger.error(f"Failed to get network graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_name}")
async def get_node_details(node_name: str) -> dict[str, Any]:
    """Get detailed information about a node."""
    try:
        client = get_neo4j()
        details = client.get_node_details(node_name)
        if not details:
            raise HTTPException(status_code=404, detail="Node not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats() -> dict[str, int]:
    """Get graph statistics."""
    try:
        client = get_neo4j()
        return client.get_graph_stats()
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
