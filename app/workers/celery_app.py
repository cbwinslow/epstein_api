"""
Celery application configuration.

This module initializes the Celery application with Redis as broker and result backend.
"""

import logging
from celery import Celery

from backend.core.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

celery_app = Celery(
    "epstein_osint",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=[
        "backend.workers.tasks",
    ],
)

celery_app.conf.update(
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

logger.info(f"Celery app initialized with broker: {settings.celery.broker_url}")
