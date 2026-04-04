import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any


class Settings(BaseSettings):
    # ====================== TELEGRAM ======================
    tg_api_id: int
    tg_api_hash: str
    tg_session_str: str
    tg_channel: str = "@studychannelus"

    # ====================== REDIS ======================
    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

    # ====================== AI ======================
    free_ai_url: str = "https://apifreellm.com/api/v1/chat"
    AI_API_KEY: str = ""  # ← Просто строка, без Field и alias

    # ====================== SOURCES ======================
    # 🔹 ВАЖНО: имена полей в нижнем регистре (как в Python-стандарте)
    tg_sources: List[Dict[str, Any]] = [
        {"name": "@techmedia"},
        {"name": "@IT_today_ru"},
    ]

    site_sources: List[Dict[str, Any]] = [
        {"name": "habr", "url": "https://habr.com/ru/rss/articles/"},
        {"name": "rbc", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
        {"name": "vc", "url": "https://vc.ru/rss"},
        {"name": "tproger", "url": "https://tproger.ru/feed/"},
    ]

    # ====================== OTHER ======================
    log_level: str = "INFO"  # 🔹 Добавлено: уровень логирования

    max_news_per_source_per_run: int = 10
    parsing_interval_minutes: int = 30
    keywords: List[str] = ["python", "ai", "startup", "telegram", "fastapi", "нейросеть",
                           "ИИ", "искусственный интеллект", "бот", "канал", "рассылка",
                           "код", "разработка", "программ", "технолог", "цифр"
                           ]

    # 🔹 Настройки Pydantic v2 (вместо class Config)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False  # LOG_LEVEL и log_level — оба работают
    )


# Глобальный экземпляр настроек
settings = Settings()
