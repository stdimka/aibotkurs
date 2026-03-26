from app.services.dedup_service import (
    generate_content_hash,
    is_duplicate,
    save_filtered,
)
from app.services.keyword_service import matches_keywords


def process_posts(redis, news: dict) -> bool:
    """
    Возвращает True, если новость прошла фильтрацию и сохранена.
    """

    # --- 1 фильтр по ключевым словам -------------------------------------
    if not matches_keywords(redis, news):
        return False

    # --- 2 генерация hash ------------------------------------------------
    content_hash = generate_content_hash(
        news["title"],
        news.get("summary"),
    )

    # --- 3 дедупликация --------------------------------------------------
    if is_duplicate(redis, content_hash):
        return False

    # --- 4 сохранить как отфильтрованную ---------------------------------
    save_filtered(redis, news, content_hash)

    return True
