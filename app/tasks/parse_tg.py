from celery import shared_task
from datetime import datetime
import asyncio

from app.config import settings
from app.news_parser.telegram import parse_tg_channel
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def parse_tg_task(self, source_name: str):
    redis = get_sync_redis()
    try:
        source_key = f"tg_sources:{source_name}"
        data = redis.hgetall(source_key)
        if not data:
            logger.warning(f"[{source_name}] Источник не найден в Redis")
            return 0

        # Получаем дату последнего поста
        last_post_raw = data.get("last_post_at")
        last_post_at = datetime.fromisoformat(last_post_raw) if last_post_raw else None

        logger.info(f"[{source_name}] Запуск парсинга Telegram-канала")

        # Запускаем асинхронный парсер
        news_items = asyncio.run(parse_tg_channel(source_name))

        if not news_items:
            logger.info(f"[{source_name}] Парсер вернул пустой результат")
            return 0

        # Сортируем по дате (сначала новые)
        news_items.sort(key=lambda x: x["published_at"], reverse=True)

        # --- Фильтрация: оставляем только свежие новости ---------------------
        if last_post_at:
            fresh_news = []
            for n in news_items:
                pub_at = n.get("published_at")
                if not pub_at:
                    continue

                # Приводим строку даты к datetime для сравнения
                if isinstance(pub_at, str):
                    try:
                        # Убираем Z и заменяем на offset, если нужно
                        pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
                    except ValueError:
                        logger.warning(f"[{source_name}] Не удалось распарсить дату: {pub_at}")
                        continue

                if pub_at > last_post_at:
                    fresh_news.append(n)
        else:
            fresh_news = news_items[:]

        # Ограничиваем количество новостей согласно настройкам
        fresh_news = fresh_news[: settings.max_news_per_source_per_run]

        if not fresh_news:
            logger.info(f"[{source_name}] Нет новых новостей после фильтрации по дате")
            return 0

        # --- Сохраняем сырые новости в Redis ---------------------------------
        for news in fresh_news:
            published_at_str = (
                news["published_at"]
                if isinstance(news["published_at"], str)
                else news["published_at"].isoformat()
            )

            news_key = f"news:raw:{source_name}:{published_at_str}"

            redis.hset(
                news_key,
                mapping={
                    "title": news.get("title", ""),
                    "url": news.get("url", ""),
                    "summary": news.get("summary", ""),
                    "source": source_name,
                    "published_at": published_at_str,
                    "raw_text": news.get("raw_text", ""),
                },
            )
            redis.expire(news_key, 3600)  # 1 час

        # --- Обновляем дату последнего обработанного поста -------------------
        newest = max(
            (n["published_at"] for n in fresh_news),
            key=lambda x: x if isinstance(x, datetime) else datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        )

        newest_str = newest.isoformat() if isinstance(newest, datetime) else str(newest)
        redis.hset(source_key, mapping={"last_post_at": newest_str})

        logger.info(f"[{source_name}] Сохранено {len(fresh_news)} новых новостей")
        return len(fresh_news)

    except Exception as exc:
        logger.error(f"[{source_name}] Критическая ошибка в parse_tg_task: {exc}")
        raise self.retry(exc=exc)
