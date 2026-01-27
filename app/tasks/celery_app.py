"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "marketing_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.discovery_tasks",
        "app.tasks.retrieval_tasks",
        "app.tasks.analysis_tasks",
        "app.tasks.scoring_tasks",
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
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

celery_app.conf.beat_schedule = {
    "discover-competitors-monthly": {
        "task": "app.tasks.discovery_tasks.discover_competitors_task",
        "schedule": crontab(day_of_month="1", hour="2", minute="0"),
        "options": {"queue": "discovery"},
    },
    "retrieve-ads-weekly": {
        "task": "app.tasks.retrieval_tasks.retrieve_all_ads_task",
        "schedule": crontab(day_of_week="monday", hour="3", minute="0"),
        "options": {"queue": "retrieval"},
    },
    "analyze-pending-ads-daily": {
        "task": "app.tasks.analysis_tasks.analyze_pending_ads_task",
        "schedule": crontab(hour="4", minute="0"),
        "options": {"queue": "analysis"},
    },
    "recalculate-percentiles-daily": {
        "task": "recalculate_percentiles",
        "schedule": crontab(hour="3", minute="30"),
        "options": {"queue": "scoring"},
    },
}

celery_app.conf.task_queues = {
    "default": {},
    "discovery": {},
    "retrieval": {},
    "analysis": {},
    "scoring": {},
}

celery_app.conf.task_routes = {
    "app.tasks.discovery_tasks.*": {"queue": "discovery"},
    "app.tasks.retrieval_tasks.*": {"queue": "retrieval"},
    "app.tasks.analysis_tasks.*": {"queue": "analysis"},
    "app.tasks.scoring_tasks.*": {"queue": "scoring"},
}
