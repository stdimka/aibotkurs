import hashlib
from datetime import datetime
from celery import shared_task

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

        response: GenerateResponse = ai_generate_post(title, summary)

        content_hash = hashlib.md5(
            f"{title}{summary}{published_at_str}".encode()
        ).hexdigest()[:16]

        generated_key = f"{GENERATED_PREFIX}:{source}:{content_hash}"

        redis.hset(
            generated_key,
            mapping={
                "original_title": response.original_title,
                "new_title": response.new_title,
                "generated_post": response.generated_post,
                "hash": content_hash,
                "source": source,
                "generated_at": datetime.now().isoformat(),
            },
        )
        redis.expire(generated_key, GENERATED_TTL)

        logger.info(f"Сгенерированный пост сохранён → {generated_key}")
        return 1

    except Exception as e:
        logger.exception(f"Ошибка генерации поста для {filtered_key}")
        raise self.retry(exc=e, countdown=60)
