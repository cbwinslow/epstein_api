"""
Model router for switching between Ollama and OpenRouter based on task complexity.

Uses dynamic model selection from OpenRouter when available.
Falls back to configured defaults or local Ollama.
"""

import asyncio
import logging
from enum import Enum
from typing import Any

import httpx

from backend.core.openrouter_fetcher import OpenRouterFetcher
from backend.core.settings import Settings

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "high_context": "google/gemini-2.5-flash-exp:free",
    "complex_reasoning": "qwen/qwen3-235b-thinking:free",
    "visual": "qwen/qwen3-vl-235b-thinking:free",
    "local": "llama3.2:3b",
}


class TaskType(str, Enum):
    """Task types for routing."""

    SIMPLE = "simple"
    EXTRACT = "extract"
    SCORE = "score"
    VISUAL = "visual"
    HIGH_CONTEXT = "high_context"


class ModelRouter:
    """Routes tasks to appropriate LLM with dynamic model selection."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ollama_base = settings.ollama.base_url
        self._openrouter_base = settings.openrouter.base_url
        self._openrouter_key = settings.openrouter.api_key
        self._cached_models: dict[str, str] = {}
        self._fetcher = OpenRouterFetcher(settings)
        self._models_initialized = False

    async def _ensure_models(self) -> None:
        """Initialize dynamic models from OpenRouter."""
        if self._models_initialized:
            return

        try:
            models = await self._fetcher.get_free_models()
            if models:
                sorted_models = sorted(
                    models,
                    key=lambda m: m.context_length or 0,
                    reverse=True,
                )
                for i, model in enumerate(sorted_models[:5]):
                    if i == 0:
                        self._cached_models["high_context"] = model.id
                    elif any("thinking" in m.id.lower() for m in sorted_models[: i + 1]):
                        self._cached_models["complex_reasoning"] = model.id
                    logger.info(f"Dynamic model: {model.id} (context: {model.context_length})")
            self._models_initialized = True
        except Exception as e:
            logger.warning(f"Failed to fetch dynamic models: {e}")
            self._models_initialized = True

    def get_provider_for_task(self, task_type: str) -> tuple[str, str]:
        """Determine which provider and model to use.

        Uses configured model from settings, or dynamic selection from cache.

        Args:
            task_type: Type of task (simple, extract, score, visual, high_context)

        Returns:
            Tuple of (provider, model_name)
        """
        asyncio.create_task(self._ensure_models())

        task_lower = task_type.lower()

        if "visual" in task_lower or "video" in task_lower or "image" in task_lower:
            return ("openrouter", self._get_model("visual"))

        if "score" in task_lower or "relationship" in task_lower:
            return ("openrouter", self._get_model("complex_reasoning"))

        if "pdf_large" in task_lower or "high_context" in task_lower:
            return ("openrouter", self._get_model("high_context"))

        if "extract" in task_lower or "entity" in task_lower:
            return ("openrouter", self._get_model("complex_reasoning"))

        return ("ollama", self._get_model("local"))

    def _get_model(self, category: str) -> str:
        """Get model for category, using cache or defaults."""
        if category in self._cached_models:
            return self._cached_models[category]

        setting_key = f"model_{category}"
        configured = getattr(self._settings.openrouter, setting_key, None)

        if configured:
            self._cached_models[category] = configured
            return configured

        return DEFAULT_MODELS.get(category, DEFAULT_MODELS["local"])

    async def generate(
        self,
        task_type: str,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """Generate response using appropriate provider.

        Args:
            task_type: Type of task.
            prompt: Input prompt.
            **kwargs: Additional generation parameters.

        Returns:
            Generated text response.
        """
        provider, model = self.get_provider_for_task(task_type)
        logger.info(f"Using {provider}:{model} for task: {task_type}")

        if provider == "ollama":
            return await self._generate_ollama(model, prompt, **kwargs)
        else:
            return await self._generate_openrouter(model, prompt, **kwargs)

    async def _generate_ollama(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """Generate using Ollama (local)."""
        url = f"{self._ollama_base}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def _generate_openrouter(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """Generate using OpenRouter (cloud)."""
        if not self._openrouter_key:
            logger.warning("OpenRouter API key not set, falling back to Ollama")
            return await self._generate_ollama(DEFAULT_MODELS["local"], prompt, **kwargs)

        url = f"{self._openrouter_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self._openrouter_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_structured(
        self,
        task_type: str,
        prompt: str,
        schema: dict[str, Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Generate structured output matching a schema with robust JSON parsing.

        Args:
            task_type: Type of task.
            prompt: Input prompt.
            schema: Expected output schema.
            max_retries: Maximum number of retries for malformed JSON.

        Returns:
            Parsed JSON response.
        """
        import json

        provider, model = self.get_provider_for_task(task_type)

        schema_prompt = f"""{prompt}

Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

JSON:"""

        last_error = None
        last_response = None
        response = None

        for attempt in range(max_retries):
            try:
                response = await self.generate(task_type, schema_prompt)

                cleaned_response = self._clean_json_response(response)

                return json.loads(cleaned_response)

            except json.JSONDecodeError as e:
                last_error = e
                last_response = response
                logger.warning(f"JSON parse attempt {attempt + 1}/{max_retries} failed: {e}")

                if attempt < max_retries - 1:
                    schema_prompt = f"""{prompt}

The previous response was not valid JSON. Please respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

JSON:"""

        logger.error(f"Failed to parse structured response after {max_retries} attempts")
        return {"error": "parse_failed", "raw": last_response, "last_error": str(last_error)}

    def _clean_json_response(self, response: str) -> str:
        """Clean LLM response to extract valid JSON.

        Handles common issues:
        - Markdown code blocks (```json ... ```)
        - Text before/after JSON
        - Trailing commas
        - Unquoted keys

        Args:
            response: Raw LLM response.

        Returns:
            Cleaned JSON string.
        """
        import re

        cleaned = response.strip()

        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            cleaned = json_match.group(0)

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        cleaned = re.sub(r",\s*([\}\]])", r"\1", cleaned)

        return cleaned

    async def refresh_models(self) -> None:
        """Refresh cached models from settings."""
        self._cached_models.clear()
        self._models_initialized = False
        await self._ensure_models()
        logger.info("Model cache refreshed")
