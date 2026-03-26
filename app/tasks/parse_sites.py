from celery import shared_task
from datetime import datetime

from app.config import settings
from app.news_parser.sites import parse_rss
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def parse_site_task(self, source_name: str):
    redis = get_sync_redis()
    try:
        source_key = f"site_sources:{source_name}"
        data = redis.hgetall(source_key)

        if not data:
            logger.warning(f"[{source_name}] Источник не найден")
            return 0

        source_url = data["url"]
        last_post_raw = data.get("last_post_at")
        last_post_at = datetime.fromisoformat(last_post_raw) if last_post_raw else None

        logger.info(f"[{source_name}] Запуск парсинга")

        news_items = parse_rss(source_url)

        if not news_items:
            return 0

        news_items.sort(key=lambda x: x["published_at"], reverse=True)

        # --- оставляем только новости, свежее last_post_at ---------------------
        if last_post_at:
            fresh_news = [
                n for n in news_items
                if n.get("published_at") and n["published_at"] > last_post_at
            ]
        else:
            fresh_news = news_items

        # --- ограничиваем число новостей -----------------------------------------
        fresh_news = fresh_news[: settings.max_news_per_source_per_run]

        if not fresh_news:
            logger.info(f"[{source_name}] Нет новых новостей")
            return 0

        # --- записываем "сырые" новости в Redis ---------------------
        for news in fresh_news:
            news_key = f"news:raw:{source_name}:{news['published_at'].isoformat()}"
            redis.hset(
                news_key,
                mapping={
                    "title": news["title"],
                    "url": news.get("link", ""),
                    "summary": news.get("summary", ""),
                    "source": source_name,
                    "published_at": news["published_at"].isoformat(),
                },
            )
            redis.expire(news_key, 3600)

        # --- обновляем дату последнего поста last_post_at --------------
        newest = max(n["published_at"] for n in fresh_news)
        redis.hset(source_key, mapping={"last_post_at": newest.isoformat()})

        logger.info(f"[{source_name}] Сохранено {len(fresh_news)} новых новостей")
        return len(fresh_news)

    except Exception as exc:
        logger.error(f"[{source_name}] Ошибка: {exc}")
        raise self.retry(exc=exc)
