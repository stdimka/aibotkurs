from app.schemas.site_sources import SiteSourceOut
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_all_site_sources(redis) -> list[SiteSourceOut]:

    sources: list[SiteSourceOut] = []

    keys = redis.keys("site_sources:*")
    if not keys:
        return []

    for key in sorted(keys):
        # Берем все поля HASH как словарь str → str
        data = redis.hgetall(key)
        if not data:
            logger.warning(f"HASH ключ пуст или неверный формат: {key}")
            continue

        name = data.get("name")
        url = data.get("url")
        last_post_at = data.get("last_post_at")
        if name and url:
            sources.append(SiteSourceOut(name=name, url=url, last_post_at=last_post_at))
        else:
            logger.warning(f"HASH ключ не содержит необходимых полей: {key}")

    return sources


if __name__ == "__main__":
    from app.redis_sync import get_sync_redis
    for source in get_all_site_sources(get_sync_redis()):
        print(source)
