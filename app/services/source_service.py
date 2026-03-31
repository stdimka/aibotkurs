from app.schemas.site_sources import SiteSourceOut
from app.utils.logging import get_logger
from app.schemas.tg_sources import TgSourceCreate, TgSourceUpdate, TgSourceOut
import logging

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


def get_all_tg_sources(redis) -> list[TgSourceOut]:

    sources: list[TgSourceOut] = []

    keys = redis.keys("tg_sources:*")
    if not keys:
        return []

    for key in sorted(keys):
        # Берем все поля HASH как словарь str → str
        data = redis.hgetall(key)
        if not data:
            logger.warning(f"HASH ключ пуст или неверный формат: {key}")
            continue

        name = data.get("name")
        last_post_at = data.get("last_post_at")
        if name:
            sources.append(TgSourceOut(name=name, last_post_at=last_post_at))
        else:
            logger.warning(f"HASH ключ не содержит необходимых полей: {key}")

    return sources


def create_tg_source(redis, source: TgSourceCreate) -> TgSourceOut:
    key = f"tg_sources:{source.name}"
    if redis.exists(key):
        logger.warning(f"Источник {source.name} уже существует")
        raise ValueError(f"Source {source.name} already exists")

    redis.hset(key, mapping={
        "name": source.name,
    })
    logger.info(f"Создан новый TG источник: {source.name}")
    return TgSourceOut(name=source.name)


def update_tg_source(redis, name: str, update_data: TgSourceUpdate) -> TgSourceOut | None:
    key = f"tg_sources:{name}"
    if not redis.exists(key):
        return None

    if update_data.name and update_data.name != name:
        # Если меняем имя — создаём новый ключ и удаляем старый
        new_key = f"tg_sources:{update_data.name}"
        data = redis.hgetall(key)
        data = {k.decode() if isinstance(k, bytes) else k: v for k, v in data.items()}
        data["name"] = update_data.name
        redis.hset(new_key, mapping=data)
        redis.delete(key)
        logger.info(f"TG источник переименован: {name} -> {update_data.name}")
        return TgSourceOut(name=update_data.name, last_post_at=data.get("last_post_at"))

    # Простое обновление без смены имени
    redis.hset(key, mapping={k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None})
    data = redis.hgetall(key)
    name_val = data.get(b"name") or data.get("name")
    last_post = data.get(b"last_post_at") or data.get("last_post_at")
    return TgSourceOut(
        name=name_val.decode() if isinstance(name_val, bytes) else name_val,
        last_post_at=last_post
    )


def delete_tg_source(redis, name: str) -> bool:
    key = f"tg_sources:{name}"
    if redis.delete(key):
        logger.info(f"TG источник удалён: {name}")
        return True
    return False


if __name__ == "__main__":
    from app.redis_sync import get_sync_redis
    for source in get_all_site_sources(get_sync_redis()):
        print(source)

