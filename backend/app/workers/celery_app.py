from celery import Celery

from app.config import Settings

settings = Settings()
celery_app = Celery("veridica", broker=str(settings.redis_url), backend=str(settings.redis_url))
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)


@celery_app.task(name="veridica.health.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "service": "veridica-worker"}