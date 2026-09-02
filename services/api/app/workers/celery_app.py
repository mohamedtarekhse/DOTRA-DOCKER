from celery import Celery

from ..config import settings

celery_app = Celery(
    "acuseek",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Cairo",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=200,
    beat_schedule={
        "cleanup-old-images-daily": {
            "task": "app.workers.indexer_tasks.cleanup_old_data",
            "schedule": 86400.0,
            "args": (90,),
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
