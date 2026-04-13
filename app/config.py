from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any


class Settings(BaseSettings):
    # ====================== TELEGRAM ======================
    TG_API_ID: int | None = None
    TG_API_HASH: str | None = None
    TG_SESSION_STR: str | None = None
    TG_CHANNEL: str = "@studychannelus"

    # ====================== REDIS ======================
    REDIS_URL: str = "redis://redis:6379/0"

    # ====================== AI ======================
    FREE_AI_URL: str = "https://apifreellm.com/api/v1/chat"
    AI_API_KEY: str = ""

    # ====================== SOURCES ======================
    TG_SOURCES: List[Dict[str, Any]] = [
        {"name": "@techmedia"},
        {"name": "@IT_today_ru"},
    ]

    SITE_SOURCES: List[Dict[str, Any]] = [
        {"name": "habr", "url": "https://habr.com/ru/rss/articles/"},
        {"name": "rbc", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
        {"name": "vc", "url": "https://vc.ru/rss"},
        {"name": "tproger", "url": "https://tproger.ru/feed/"},
    ]

    # ====================== OTHER ======================
    LOG_LEVEL: str = "INFO"

    MAX_NEWS_PER_SOURCE_PER_RUN: int = 10
    PARSING_INTERVAL_MINUTES: int = 30

    KEYWORDS: List[str] = [
        "python", "ai", "нейросеть", "искусственный интеллект", "ИИ",
        "startup", "стартап", "telegram", "бот", "fastapi",
        "разработка", "программирование", "it", "айти", "технологии",
        "gpt", "llm", "машинное обучение", "openai", "groq",
        "нейронные сети", "генеративный", "programming", "developer", "код", "data science"
    ]

    # ====================== ОБРАТНАЯ СОВМЕСТИМОСТЬ ======================
    # Эти свойства нужны, чтобы старый код (parse_sites, parse_tg, publisher и т.д.) не падал
    @property
    def redis_url(self):
        return self.REDIS_URL

    @property
    def max_news_per_source_per_run(self):
        return self.MAX_NEWS_PER_SOURCE_PER_RUN

    @property
    def parsing_interval_minutes(self):
        return self.PARSING_INTERVAL_MINUTES

    @property
    def keywords(self):
        return self.KEYWORDS

    @property
    def site_sources(self):
        return self.SITE_SOURCES

    @property
    def tg_sources(self):
        return self.TG_SOURCES

    @property
    def free_ai_url(self):
        return self.FREE_AI_URL

    @property
    def tg_channel(self):
        return self.TG_CHANNEL

    @property
    def tg_api_id(self):
        return self.TG_API_ID

    @property
    def tg_api_hash(self):
        return self.TG_API_HASH

    @property
    def tg_session_str(self):
        return self.TG_SESSION_STR


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


# Глобальный экземпляр настроек
settings = Settings()
