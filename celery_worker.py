from celery_app import celery_app

# чтобы Celery увидел задачи
import app.tasks.parse_sites  # noqa