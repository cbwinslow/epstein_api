"""
Dynamic OpenRouter model fetcher.

Fetches available free models from OpenRouter API and caches them in Redis.
The free tier changes frequently, so this utility ensures we always have
the latest available models.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx
import redis

from backend.core.settings import Settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"
CACHE_KEY = "openrouter_free_models"
CACHE_TTL_SECONDS = 86400  # 24 hours


@dataclass
class ModelInfo:
    """Information about an OpenRouter model."""

    id: str
    name: str
    pricing_prompt: float
    pricing_completion: float
    context_length: int | None


class OpenRouterFetcher:
    """Fetches and caches free models from OpenRouter."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._redis_client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            decode_responses=True,
        )

    async def get_free_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """Get list of free models from OpenRouter.

        Args:
            force_refresh: Force refresh from API even if cached.

        Returns:
            List of free ModelInfo objects.
        """
        if not force_refresh:
            cached = self._get_cached_models()
            if cached:
                return cached

        models = await self._fetch_models_from_api()
        self._cache_models(models)
        return models

    def _get_cached_models(self) -> list[ModelInfo] | None:
        """Get models from Redis cache."""
        try:
            cached_data = self._redis_client.get(CACHE_KEY)
            if cached_data:
                logger.info("Returning cached free models")
                data = json.loads(cached_data)
                return [ModelInfo(**m) for m in data]
        except Exception as e:
            logger.warning(f"Failed to get cached models: {e}")
        return None

    def _cache_models(self, models: list[ModelInfo]) -> None:
        """Cache models in Redis."""
        try:
            data = [model.__dict__ for model in models]
            self._redis_client.setex(
                CACHE_KEY,
                CACHE_TTL_SECONDS,
                json.dumps(data),
            )
            logger.info(f"Cached {len(models)} free models")
        except Exception as e:
            logger.warning(f"Failed to cache models: {e}")

    async def _fetch_models_from_api(self) -> list[ModelInfo]:
        """Fetch models from OpenRouter API."""
        logger.info("Fetching models from OpenRouter API")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(OPENROUTER_API_URL)
            response.raise_for_status()

            data = response.json()
            models = []

            for model_data in data.get("data", []):
                pricing = model_data.get("pricing", {})
                prompt_price = float(pricing.get("prompt", 0) or 0)
                completion_price = float(pricing.get("completion", 0) or 0)

                if prompt_price == 0 and completion_price == 0:
                    model_info = ModelInfo(
                        id=model_data["id"],
                        name=model_data.get("name", model_data["id"]),
                        pricing_prompt=prompt_price,
                        pricing_completion=completion_price,
                        context_length=model_data.get("context_length"),
                    )
                    models.append(model_info)

            logger.info(f"Found {len(models)} free models")
            return models

    def get_best_free_model(self) -> str | None:
        """Get the best available free model (highest context length).

        Returns:
            Model ID or None.
        """
        import asyncio

        try:
            models = asyncio.get_event_loop().run_until_complete(self.get_free_models())
            if not models:
                return None

            sorted_models = sorted(
                models,
                key=lambda m: m.context_length or 0,
                reverse=True,
            )
            return sorted_models[0].id
        except Exception:
            return None


async def get_free_openrouter_models() -> list[dict[str, Any]]:
    """Convenience function to get free models.

    Returns:
        List of free model dictionaries.
    """
    from backend.core.settings import get_settings

    settings = get_settings()
    fetcher = OpenRouterFetcher(settings)
    models = await fetcher.get_free_models()
    return [
        {
            "id": m.id,
            "name": m.name,
            "context_length": m.context_length,
        }
        for m in models
    ]
