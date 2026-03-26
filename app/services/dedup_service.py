import hashlib
import re

PUBLISHED_TTL = 7 * 24 * 60 * 60  # 1 неделя
FILTERED_TTL = 60 * 60  # 1 час


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def generate_content_hash(title: str, summary: str | None = None) -> str:
    base = f"{title} {summary or ''}"
    normalized = normalize_text(base)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def is_duplicate(redis, content_hash: str) -> bool:
    return redis.exists(f"published_hash:{content_hash}") == 1


def mark_as_published(redis, content_hash: str):
    redis.set(
        f"published_hash:{content_hash}",
        1,
        ex=PUBLISHED_TTL,
    )


def save_filtered(redis, news: dict, content_hash: str):
    redis.hset(
        f"filtered_news:{content_hash}",
        mapping={
            "title": news["title"],
            "url": news.get("url", ""),
            "summary": news.get("summary", ""),
            "source": news["source"],
            "published_at": news["published_at"],
        },
    )
    # --- Добавляем TTL ключ сроком на 1 час: 60 * 60 -----------------
    redis.expire(f"filtered_news:{content_hash}", FILTERED_TTL)
