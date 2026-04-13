from celery import Celery
from app.config import settings
from celery.schedules import crontab

celery_app = Celery(
    "news_parser",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[

        "app.tasks.parse_sites",
        "app.tasks.parse_tg",
        "app.tasks.filter",
        "app.tasks.generate",
        "app.tasks.publish",
        "app.tasks.pipeline",

    ],

)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 минут максимум на задачу
    task_soft_time_limit=270,
)


# ==================== CELERY BEAT SCHEDULE ====================
celery_app.conf.beat_schedule = {
    'run-news-pipeline-every-30-min': {
        'task': 'run_pipeline_task',                    # ← упрощённое имя
        'schedule': crontab(minute='*/30'),
    },
}