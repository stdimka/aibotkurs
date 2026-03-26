from celery import Celery
from app.config import settings

celery_app = Celery(
    "news_parser",
    broker=settings.redis_url,     # redis://localhost:6379/0
    backend=settings.redis_url,
    include=[

        "app.tasks.parse_sites",
        "app.tasks.filter",
        "app.tasks.generate",

    ],

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
