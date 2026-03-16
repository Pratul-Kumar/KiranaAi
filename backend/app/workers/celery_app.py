from celery import Celery
from app.core.config import get_settings
from app.core.logging_config import setup_logging

settings = get_settings()
setup_logging()

celery_app = Celery(
    "znshop",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
