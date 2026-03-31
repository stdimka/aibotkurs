# --- Telegram ---------------------------------------------------------------
API_ID =Замени на свой
API_HASH = "Замени на свой"
CHANNEL_USERNAME = "@Замени на свой"
SESSION_STRING = "Замени на свой"

# --- Telegram-каналы и сайты -------------------------------------------------
TG_SOURCES = [
    {"name": "@techmedia"},
    {"name": "@IT_today_ru"},
]


# --- AI SERVICE --------------------------------------------------------------
AI_API_KEY = "apf_p519oc0a4wgrhw9mblpx2ah6"

# --- Redis -------------------------------------------------------------------
REDIS_URL = "redis://127.0.0.1:6379/0"

# --- Периодичность парсинга (Celery Beat) ------------------------------------
PARSING_INTERVAL_MINUTES = 30

# --- Дефолтные ключевые слова ------------------------------------------------
KEYWORDS = ["python", "ai", "startup", "telegram", "fastapi"]


SITE_SOURCES = [
    {"name": "habr", "url": "https://habr.com/ru/rss/"},
    {"name": "rbc", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
    {"name": "vc", "url": "https://vc.ru/rss"},
    {"name": "tproger", "url": "https://tproger.ru/feed/"},
]

MAX_NEWS_PER_SOURCE_PER_RUN = 10