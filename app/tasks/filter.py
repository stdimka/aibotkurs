import hashlib
from celery import shared_task

from app.redis_sync import get_sync_redis
from app.services.keyword_service import get_all_keywords  # сервис для ключевых слов
from app.utils.logging import get_logger

logger = get_logger(__name__)

FILTERED_TTL = 60 * 60  # 1 час
DUP_TTL = 7 * 24 * 60 * 60  # 1 неделя для индекса хешей

@shared_task(bind=True, name="filter_posts", max_retries=2)
def filter_posts_task(self, previous_results: list | None = None):

    """
    Задача фильтрации сырых новостей.
    Берёт новости из news:raw:*, фильтрует по ключевым словам и дедупликации,
    сохраняет отфильтрованные в news:filtered:*
    """

    redis = get_sync_redis()

    try:
        # --- получаем ключи сырых новостей ---
        keys = redis.keys("news:raw:*")
        if not keys:
            logger.info("Сырых новостей нет")
            return 0

        # --- получаем список ключевых слов ---
        keywords = get_all_keywords(redis)
        keywords = set(kw.lower() for kw in keywords)

        processed = 0

        for key in keys:
            data = redis.hgetall(key)
            if not data:
                continue

            title = data.get("title", "")
            summary = data.get("summary", "")
            source = data.get("source")
            published_at = data.get("published_at")

            content = f"{title} {summary}".lower()
            logger.info(f"[{source}] Пост: {title[:50]}..., проверяем на ключевые слова")

            # --- фильтр по ключевым словам ---
            if keywords:
                if any(kw in content for kw in keywords):
                    logger.info(f"[{source}] Прошёл фильтр по ключевым словам")
                else:
                    logger.info(f"[{source}] НЕ прошёл фильтр по ключевым словам")
                    continue

            # --- дедупликация по хешу ---
            hash_digest = hashlib.md5(content.encode()).hexdigest()
            dup_key = f"news:dup:{hash_digest}"

            if redis.exists(dup_key):
                logger.debug(f"[{source}] Пропущено, дубликат {hash_digest}")
                continue  # уже есть, пропускаем

            # --- сохраняем фильтрованную новость ---
            filtered_key = f"news:filtered:{source}:{published_at}"
            redis.hset(
                filtered_key,
                mapping={
                    "title": title,
                    "url": data.get("url", ""),
                    "summary": summary,
                    "source": source,
                    "published_at": published_at,
                },
            )
            redis.expire(filtered_key, FILTERED_TTL)
            logger.info(f"[{source}] Сохранена фильтрованная новость: {title[:50]}...")

            # --- помечаем как обработанную (дубликат) ---
            # await redis.set(dup_key, 1, ex=DUP_TTL)
            redis.hset(
                dup_key,
                mapping={
                    "hash": hash_digest,
                    "title": title,
                    "summary": summary,
                    "source": data.get("source"),
                    "published_at": data.get("published_at"),
                },
            )
            redis.expire(dup_key, DUP_TTL)

            processed += 1

        logger.info(f"Отфильтровано и сохранено: {processed}")
        return processed

    except Exception as e:
        logger.error("Критическая ошибка в задаче фильтрации", exc_info=True)
        raise self.retry(exc=e, countdown=30)
