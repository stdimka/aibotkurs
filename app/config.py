from pydantic import BaseModel
from local_settings import *  # noqa

try:
    from local_settings import (
        API_ID, API_HASH, CHANNEL_USERNAME,
        AI_API_KEY, REDIS_URL,
        PARSING_INTERVAL_MINUTES, KEYWORDS,
        TG_SOURCES, SITE_SOURCES,
    )
except ImportError:
    raise ImportError("local_settings.py не найден в корне проекта")


class Settings(BaseModel):
    tg_api_id: int = API_ID
    tg_api_hash: str = API_HASH
    tg_session_str: str = SESSION_STRING
    tg_channel: str = CHANNEL_USERNAME
    ai_api_key: str = AI_API_KEY
    redis_url: str = REDIS_URL
    parsing_interval_minutes: int = PARSING_INTERVAL_MINUTES
    words: list[str] = KEYWORDS
    tg_sources: list[str] = TG_SOURCES
    site_sources: list[dict] = SITE_SOURCES
    log_level: str = "INFO"
    max_news_per_source_per_run: int = MAX_NEWS_PER_SOURCE_PER_RUN

settings = Settings.model_validate({})   # просто для валидации типов



