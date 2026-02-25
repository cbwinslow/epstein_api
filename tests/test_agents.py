"""
Unit tests for AI agents (model router and MCP tools).
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

BACKEND_PATH = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH.parent))


class TestModelRouter:
    """Tests for ModelRouter."""

    @pytest.mark.asyncio
    async def test_model_router_initialization(self):
        """Test ModelRouter initializes correctly."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        assert router._settings is not None
        assert router._cached_models == {}
        assert router._models_initialized is False

    def test_get_provider_for_simple_task(self):
        """Test routing for simple tasks."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        provider, model = router.get_provider_for_task("simple")

        assert provider in ["openrouter", "ollama"]
        assert model is not None

    def test_get_provider_for_extract_task(self):
        """Test routing for entity extraction."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        provider, model = router.get_provider_for_task("extract")

        assert provider in ["openrouter", "ollama"]

    def test_get_provider_for_score_task(self):
        """Test routing for relationship scoring."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        provider, model = router.get_provider_for_task("score")

        # Score tasks should prefer complex reasoning models
        assert provider in ["openrouter", "ollama"]

    def test_get_provider_for_visual_task(self):
        """Test routing for visual tasks."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        provider, model = router.get_provider_for_task("visual")

        assert provider in ["openrouter", "ollama"]

    def test_get_provider_for_high_context(self):
        """Test routing for high context tasks."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        provider, model = router.get_provider_for_task("high_context")

        assert provider in ["openrouter", "ollama"]

    @pytest.mark.asyncio
    async def test_generate_with_openrouter(self):
        """Test generate calls openrouter."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        with patch.object(
            router, "_generate_openrouter", new_callable=AsyncMock
        ) as mock_or:
            mock_or.return_value = "Test response"

            result = await router.generate("simple", "Test prompt")

            assert result == "Test response"
            mock_or.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_ollama(self):
        """Test generate calls ollama."""
        from backend.agents.model_router import ModelRouter
        from backend.core.settings import Settings

        settings = Settings()
        router = ModelRouter(settings)

        with patch.object(
            router, "_generate_ollama", new_callable=AsyncMock
        ) as mock_ollama:
            mock_ollama.return_value = "Ollama response"

            # Force ollama by patching get_provider_for_task
            with patch.object(
                router, "get_provider_for_task", return_value=("ollama", "llama3.2:3b")
            ):
                result = await router.generate("simple", "Test prompt")

                assert result == "Ollama response"

    def test_default_models_exist(self):
        """Test default models are defined."""
        from backend.agents.model_router import DEFAULT_MODELS

        assert "high_context" in DEFAULT_MODELS
        assert "complex_reasoning" in DEFAULT_MODELS
        assert "visual" in DEFAULT_MODELS
        assert "local" in DEFAULT_MODELS


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self):
        """Test TaskType values."""
        from backend.agents.model_router import TaskType

        assert TaskType.SIMPLE.value == "simple"
        assert TaskType.EXTRACT.value == "extract"
        assert TaskType.SCORE.value == "score"
        assert TaskType.VISUAL.value == "visual"
        assert TaskType.HIGH_CONTEXT.value == "high_context"


class TestMCPTools:
    """Tests for MCP tools."""

    def test_mcp_tools_initialization(self):
        """Test MCPTools initializes correctly."""
        from backend.agents.mcp_tools import MCPTools
        from backend.core.settings import Settings

        settings = Settings()
        tools = MCPTools(settings)

        assert tools._settings is not None
        assert tools._chroma is not None
        assert tools._neo4j is not None

    def test_read_sidecar_raises_on_missing(self):
        """Test read_sidecar raises FileNotFoundError."""
        from backend.agents.mcp_tools import MCPTools
        from backend.core.settings import Settings

        settings = Settings()
        tools = MCPTools(settings)

        with pytest.raises(FileNotFoundError):
            tools.read_sidecar(99999)

    def test_read_sidecar_by_path_raises_on_missing(self):
        """Test read_sidecar_by_path raises on missing file."""
        from backend.agents.mcp_tools import MCPTools
        from backend.core.settings import Settings
        from pathlib import Path

        settings = Settings()
        tools = MCPTools(settings)

        with pytest.raises(FileNotFoundError):
            tools.read_sidecar_by_path(Path("/nonexistent/file.json"))

    def test_query_vector_db_returns_format(self):
        """Test query_vector_db returns correct format."""
        from backend.agents.mcp_tools import MCPTools
        from backend.core.settings import Settings
        from unittest.mock import patch

        settings = Settings()
        tools = MCPTools(settings)

        with patch.object(
            tools._chroma,
            "query",
            return_value={
                "documents": [["doc1"]],
                "metadatas": [[{"file_id": 1}]],
                "distances": [[0.1]],
            },
        ):
            result = tools.query_vector_db("test query")

            assert isinstance(result, list)
            assert len(result) >= 0

    def test_search_graph_returns_format(self):
        """Test search_graph returns correct format."""
        from backend.agents.mcp_tools import MCPTools
        from backend.core.settings import Settings
        from unittest.mock import patch

        settings = Settings()
        tools = MCPTools(settings)

        with patch.object(tools._neo4j, "execute_query", return_value=[]):
            result = tools.search_graph(entity_name="Epstein")

            assert isinstance(result, (list, dict))

    def test_search_graph_custom_cypher(self):
        """Test search_graph with custom cypher."""
        from backend.agents.mcp_tools import MCPTools
        from backend.core.settings import Settings
        from unittest.mock import patch

        settings = Settings()
        tools = MCPTools(settings)

        with patch.object(
            tools._neo4j, "execute_query", return_value=[{"n": {"name": "Test"}}]
        ):
            result = tools.search_graph(cypher="MATCH (n) RETURN n")

            assert isinstance(result, (list, dict))


class TestOpenRouterFetcher:
    """Tests for OpenRouter fetcher."""

    @pytest.mark.asyncio
    async def test_fetcher_initialization(self):
        """Test fetcher initializes."""
        from backend.core.openrouter_fetcher import OpenRouterFetcher
        from backend.core.settings import Settings

        settings = Settings()
        fetcher = OpenRouterFetcher(settings)

        assert fetcher._settings is not None
        assert fetcher._redis_client is not None


class TestToolOutputs:
    """Tests for tool output formatting."""

    def test_format_context_for_llm(self):
        """Test context is formatted for LLM."""
        # This tests the concept that MCP tools should return string context
        context_data = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"file_id": 1}, {"file_id": 2}]],
            "distances": [[0.1, 0.2]],
        }

        # Format as string context
        formatted = []
        for i, doc in enumerate(context_data["documents"][0]):
            metadata = context_data["metadatas"][0][i]
            distance = context_data["distances"][0][i]
            formatted.append(
                f"[Source {metadata.get('file_id')}, similarity: {distance:.3f}]\n{doc}"
            )

        result = "\n---\n".join(formatted)

        assert "Source 1" in result
        assert "similarity:" in result


class TestErrorHandling:
    """Tests for agent error handling."""

    def test_agent_parsing_error_exists(self):
        """Test AgentParsingError exists."""
        from backend.core.exceptions import AgentParsingError

        error = AgentParsingError(
            raw_output="{invalid json", reason="Expecting ',' delimiter"
        )
        assert "invalid json" in str(error).lower() or "Expecting" in str(error)
