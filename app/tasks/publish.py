import asyncio
import time
from celery import shared_task

from app.telegram.publisher import telegram_publisher
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, name="publish_to_telegram")
def publish_to_telegram_task(self, generated_key: str):
    redis = get_sync_redis()
    try:
        raw_data = redis.hgetall(generated_key)
        if not raw_data:
            logger.error(f"Сгенерированный пост не найден: {generated_key}")
            return 0

        # Декодируем bytes
        data = {
            (k.decode("utf-8") if isinstance(k, bytes) else k):
            (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in raw_data.items()
        }

        is_published = str(data.get("is_published", "")).strip().lower() in ("1", "true", "yes")
        if is_published:
            logger.info(f"Пост уже опубликован ранее: {generated_key}")
            return 0

        title = data.get("new_title") or data.get("original_title") or "Без заголовка"
        text = data.get("generated_post", "")

        # 🔹 Извлечение изображения (самое надёжное)
        image_url = None
        for key in ["image", "image_url", b"image", b"image_url"]:
            val = data.get(key)
            if val:
                if isinstance(val, bytes):
                    val = val.decode("utf-8", errors="ignore")
                if val and str(val).startswith("http"):
                    image_url = val
                    break

        logger.info(f"Публикация: {title[:70]}... | Изображение: {'✅' if image_url else '❌'}")

        success = asyncio.run(
            telegram_publisher.publish_post(
                title=title,
                text=text,
                image_url=image_url
            )
        )

        if success:
            redis.hset(generated_key, mapping={
                "is_published": "1",
                "published_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            logger.info(f"✅ Пост успешно опубликован → {generated_key}")
            return 1
        else:
            logger.warning(f"Не удалось опубликовать пост {generated_key}")
            return 0

    except Exception as e:
        logger.exception(f"Ошибка публикации поста {generated_key}")
        raise self.retry(exc=e, countdown=30)
