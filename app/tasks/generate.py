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
    """Помощник: декодирует bytes → str"""
    decoded = {}
    for k, v in raw_data.items():
        key = k.decode("utf-8") if isinstance(k, bytes) else k
        value = v.decode("utf-8") if isinstance(v, bytes) else v
        decoded[key] = value
    return decoded


@shared_task(bind=True, name="generate_post", max_retries=2)
def generate_post_task(self, filtered_key: str):
    """
    Генерация AI-поста с сохранением изображения.
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
        image_url = data.get("image") or data.get("image_url") or ""

        if not title or not summary:
            logger.error(f"Недостаточно данных для генерации: {filtered_key}")
            return 0

        logger.info(f"Генерация поста для [{source}] → {title[:70]}...")

        response: GenerateResponse = asyncio.run(ai_generate_post(title, summary))

        if not response.success:
            logger.error(f"❌ Не удалось сгенерировать пост: {response.error}")
            return 0

        content_hash = hashlib.md5(f"{title}{summary}".encode()).hexdigest()[:16]
        generated_key = f"{GENERATED_PREFIX}:{source}:{content_hash}"

        if redis.exists(generated_key):
            logger.info(f"Пост уже был сгенерирован ранее → {generated_key}")
            return 1

        # === ИСПРАВЛЕННЫЙ БЛОК СОХРАНЕНИЯ С ИЗОБРАЖЕНИЕМ ===
        image_url = data.get("image") or data.get("image_url") or ""

        redis.hset(
            generated_key,
            mapping={
                "title": title,
                "summary": summary,
                "source": source,
                "generated_post": response.content or "",
                "is_published": "0",
                "generated_at": datetime.utcnow().isoformat(),

                # Главное исправление — сохраняем изображение
                "image": image_url,

                # Для совместимости
                "original_title": title,
                "new_title": title,
            }
        )

        redis.expire(generated_key, GENERATED_TTL)
        deleted = redis.delete(filtered_key)

        logger.info(
            f"Сгенерированный пост сохранён → {generated_key} | image: {'✅' if image_url else '❌'} | filtered удалён: {deleted}")
        return 1


    except Exception as e:
        logger.exception(f"Ошибка генерации поста для {filtered_key}")
        raise self.retry(exc=e, countdown=60)
