import redis.asyncio as aioredis

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def initialize_default_settings(redis: aioredis.Redis) -> None:
    """
    Создаёт дефолтные ключевые слова / источники при первом запуске,
    если их ещё нет в Redis.
    """
    # --- Инициализация ключевых слов ---------------------------------------
    default_keywords = settings.words

    count_before = await redis.scard("keywords")
    if count_before == 0:
        logger.info("Redis пуст → добавляем дефолтные ключевые слова")
        for kw in default_keywords:
            await redis.sadd("keywords", kw)
        logger.info(f"Добавлено {len(default_keywords)} дефолтных ключевых слов")
    else:
        logger.debug(f"Ключевые слова уже существуют ({count_before} шт), пропускаем инициализацию")

    # --- Инициализация сайтов -----------------------------------------------
    default_sites = settings.site_sources

    for site in default_sites:
        key = f"site_sources:{site['name']}"
        exists = await redis.exists(key)
        if not exists:
            logger.info("Добавляем дефолтный источник: %s", site['name'])
            await redis.hset(key, mapping={
                "name": site["name"],
                "url": site["url"]
            })
        else:
            logger.debug(f"Источник site_sources: {site['name']} уже существует!")

    # --- Инициализация телеграм-каналов ----------------------------------------
    # Добавим позже
