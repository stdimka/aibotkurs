import redis
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_sync_redis: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    """Ленивая инициализация sync Redis-пула для Celery задач"""
    global _sync_redis

    if _sync_redis is None:
        logger.info("Инициализация sync Redis пула для Celery...")

        _sync_redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_keepalive=True,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            max_connections=20,
        )

        # Проверка подключения сразу при создании
        try:
            _sync_redis.ping()
            logger.info("sync Redis пул успешно инициализирован и проверен")
        except Exception as e:
            logger.error(f"Не удалось подключиться к sync Redis: {e}")
            _sync_redis = None
            raise RuntimeError(f"Redis connection failed: {e}") from e

    return _sync_redis
