from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.dependencies import init_redis_pool

from app.utils.logging import setup_logging, get_logger
from app.api.v1 import keywords, site_sources, tg_sources, posts, filtered_posts, history, generate  # импортируем роутеры по мере готовности
from app.utils.initialization import initialize_default_settings

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan-события: запуск при старте / очистка при остановке
    """
    # --- Настройка логирования (один раз при старте) -------------------
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Запуск приложения aibot ...")

    # --- Инициализация Redis -------------------------------------------
    redis_initialized = False
    try:
        redis_pool = await init_redis_pool()
        app.state.redis = redis_pool
        redis_initialized = True
        await initialize_default_settings(redis_pool)
        logger.info("Дефолтные настройки проверены / инициализированы")
    except Exception as e:
        logger.error(f"Ошибка инициализации начальных настроек в Redis: {e}")
        app.state.redis = None
        # не падаем — приложение может продолжить работу

    yield

    # --- Shutdown ----------------------------------------------------
    logger.info("Остановка приложения aibot ...")
    if redis_initialized:
        try:
            redis = getattr(app.state, "redis", None)
            if redis:
                await redis.close()
                await redis.connection_pool.disconnect()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии Redis пула: {e}")
    logger.info("Приложение остановлено")

# --- Само приложение -------------------------------------------------
app = FastAPI(
    title="AI News Telegram Bot",
    description="Автоматизированный новостной канал с AI-генерацией постов",
    lifespan=lifespan
)


# --- Подключаем роутеры (по мере реализации) --------------------------
app.include_router(keywords.router, prefix="/api/v1", tags=["keywords"])
app.include_router(site_sources.router, prefix="/api/v1", tags=["site_sources"])
app.include_router(tg_sources.router, prefix="/api/v1", tags=["tg_sources"])
app.include_router(posts.router, prefix="/api/v1", tags=["posts"])
app.include_router(filtered_posts.router, prefix="/api/v1", tags=["filtered_posts"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])


@app.get("/health", response_model=dict, tags=["system"])
async def health_check(request: Request):
    redis = getattr(request.app.state, "redis", None)

    redis_ok = False
    if redis:
        try:
            redis_ok = await redis.ping()
        except Exception:
            redis_ok = False

    status_code = (
        status.HTTP_200_OK if redis_ok
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        content={
            "status": "healthy" if redis_ok else "degraded",
            "redis": "connected" if redis_ok else "disconnected",
        },
        status_code=status_code,
    )



# Настройка шаблонов (папка templates должна быть в корне проекта)
templates = Jinja2Templates(directory="templates")


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Простая админ-панель"""
    return templates.TemplateResponse("admin.html", {"request": request})