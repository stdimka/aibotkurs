import redis.asyncio as aioredis
from fastapi import Request

from app.config import settings   # ← здесь REDIS_URL и другие настройки
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Один глобальный пул подключений (хороший производительный вариант)
# Создаётся один раз при старте приложения
redis: aioredis.Redis | None = None


async def init_redis_pool() -> aioredis.Redis:
    """Инициализация пула подключений к Redis (вызывается в lifespan)"""

    url = settings.redis_url
    logger.debug(f"Инициализация Redis пула: {url}")

    try:
        # Сначала создаём клиента
        redis = await aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            max_connections=20,
            socket_keepalive=True,
        )

        # Проверяем подключение
        pong = await redis.ping()
        logger.info(f"Redis пул инициализирован успешно → PING → {pong}")
        return redis

    except Exception as e:
        logger.critical(f"Критическая ошибка: не удалось подключиться к Redis: {e}")
        redis = None  # явно сбрасываем
        raise RuntimeError(f"Не удалось подключиться к Redis → {e}")


async def get_redis(request: Request) -> aioredis.Redis:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise RuntimeError("Redis is not initialized")
    return redis
