import hashlib
from datetime import datetime
from celery import shared_task
import asyncio
from app.ai.generator import ai_generate_post
from app.redis_sync import get_sync_redis
from app.schemas.generate import GenerateResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

GENERATED_TTL = 24 * 60 * 60
GENERATED_PREFIX = "news:generated"


def _decode_redis_hash(raw_data: dict) -> dict:
    """Помощник: декодирует bytes → str (redis-py по умолчанию отдаёт bytes)"""
    decoded = {}
    for k, v in raw_data.items():
        key = k.decode("utf-8") if isinstance(k, bytes) else k
        value = v.decode("utf-8") if isinstance(v, bytes) else v
        decoded[key] = value
    return decoded


@shared_task(bind=True, name="generate_post", max_retries=2)
def generate_post_task(self, filtered_key: str):
    """
    Генерация AI-поста.
    Всегда возвращает int: 1 = успех, 0 = провал (чтобы sum() в pipeline не падал).
    """
    redis = get_sync_redis()

    try:
        raw_data = redis.hgetall(filtered_key)
        if not raw_data:
            logger.warning(f"Отфильтрованная новость не найдена: {filtered_key}")
            return 0

        data = _decode_redis_hash(raw_data)

        title = data.get("title", "")
        summary = data.get("summary", "")
        source = data.get("source", "unknown")
        published_at_str = data.get("published_at", "")

        if not title or not summary:
            logger.error(f"Недостаточно данных для генерации: {filtered_key}")
            return 0

        logger.info(f"Генерация поста для [{source}] → {title[:70]}...")

        response: GenerateResponse = asyncio.run(ai_generate_post(title, summary)
                                                 )
        if not response.success:
            logger.error(f"❌ Не удалось сгенерировать пост: {response.error}")
            # Возвращаем 0 — задача не выполнена, но не падаем с ошибкой
            return 0

        content_hash = hashlib.md5(
            f"{title}{summary}".encode()
        ).hexdigest()[:16]

        generated_key = f"{GENERATED_PREFIX}:{source}:{content_hash}"

        # Добавляем защиту от повторной генерации
        if redis.exists(generated_key):
            logger.info(f"Пост уже был сгенерирован ранее → {generated_key}")
            return 1

        # app/tasks/generate.py — внутри generate_post_task, после получения response:

        # 🔹 Безопасное извлечение полей с дефолтными значениями
        redis.hset(
            generated_key,
            mapping={
                # Обязательные поля
                "title": str(title) if title else "",
                "summary": str(summary) if summary else "",
                "source": str(source) if source else "",
                "hash": str(content_hash) if content_hash else "",
                "generated_content": str(response.content) if response.content else "",
                "is_published": "0",
                "created_at": datetime.utcnow().isoformat(),
                "generated_at": datetime.now().isoformat(),

                # Опциональные поля (с дефолтами)
                "original_title": str(getattr(response, "original_title", title)) if getattr(response, "original_title",
                                                                                             title) else str(title),
                "new_title": str(getattr(response, "new_title", title)) if getattr(response, "new_title",
                                                                                   title) else str(title),
                "generated_post": str(getattr(response, "generated_post", response.content)) if getattr(response,
                                                                                                        "generated_post",
                                                                                                        response.content) else "",
            },
        )

        redis.expire(generated_key, GENERATED_TTL)
        deleted = redis.delete(filtered_key)
        logger.info(f"Сгенерированный пост сохранён → {generated_key} | filtered удалён: {deleted}")
        return 1

    except Exception as e:
        logger.exception(f"Ошибка генерации поста для {filtered_key}")
        raise self.retry(exc=e, countdown=60)
