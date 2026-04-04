from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import init_redis_pool
from app.utils.logging import setup_logging, get_logger
from app.utils.initialization import initialize_default_settings


from app.redis_sync import get_sync_redis
import json
from datetime import datetime


# Импортируем роутеры
from app.api.v1 import (
    keywords,
    site_sources,
    tg_sources,
    posts,
    filtered_posts,
    history,
    generate
)

# Импорт задачи пайплайна
from app.tasks.pipeline import run_pipeline_task


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan события: запуск и остановка приложения"""
    logger = get_logger(__name__)
    logger.info("Запуск приложения aibot ...")

    # Инициализация Redis
    redis_initialized = False
    try:
        redis_pool = await init_redis_pool()
        app.state.redis = redis_pool
        redis_initialized = True
        await initialize_default_settings(redis_pool)
        logger.info("Дефолтные настройки проверены / инициализированы")
    except Exception as e:
        logger.error(f"Ошибка инициализации Redis: {e}")
        app.state.redis = None

    yield

    # Shutdown
    logger.info("Остановка приложения aibot ...")
    if redis_initialized and hasattr(app.state, "redis"):
        try:
            redis = app.state.redis
            await redis.close()
            await redis.connection_pool.disconnect()
        except Exception as e:
            logger.warning(f"Ошибка закрытия Redis: {e}")

    logger.info("Приложение остановлено")


# Создаём приложение
app = FastAPI(
    title="AI News Telegram Bot",
    description="Автоматизированный новостной канал с генерацией постов через ИИ",
    lifespan=lifespan
)


# Подключаем роутеры
app.include_router(keywords.router, prefix="/api/v1", tags=["keywords"])
app.include_router(site_sources.router, prefix="/api/v1", tags=["site_sources"])
app.include_router(tg_sources.router, prefix="/api/v1", tags=["tg_sources"])
app.include_router(posts.router, prefix="/api/v1", tags=["posts"])
app.include_router(filtered_posts.router, prefix="/api/v1", tags=["filtered_posts"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])


# ====================== АДМИНКА ======================
templates = Jinja2Templates(directory="templates")


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Главная страница админ-панели"""
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/tg_sources", response_class=HTMLResponse)
async def tg_sources_page(request: Request):
    """Страница управления TG-каналами"""
    return templates.TemplateResponse("tg_sources.html", {"request": request})

@app.get("/site_sources", response_class=HTMLResponse)
async def site_sources_page(request: Request):
    """Страница управления сайтами (RSS)"""
    return templates.TemplateResponse("site_sources.html", {"request": request})

@app.post("/admin/run_pipeline")
async def trigger_pipeline():
    """Запуск полного пайплайна вручную"""
    try:
        # Используем строку названия задачи, чтобы Celery точно её нашёл
        from celery_app import celery_app
        celery_app.send_task("run_pipeline_task")

        return {
            "status": "success",
            "message": "Пайплайн успешно запущен в фоне."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка запуска пайплайна: {str(e)}"
        }


@app.get("/admin/recent_posts")
async def get_recent_posts():
    """Возвращает последние посты для админки (сначала опубликованные, потом сгенерированные)"""
    try:
        from app.redis_sync import get_sync_redis
        redis = get_sync_redis()

        keys = redis.keys("news:generated:*")
        if not keys:
            return {"posts": []}

        posts = []
        for key in keys:
            data = redis.hgetall(key)
            if not data:
                continue

            try:
                title = data.get(b"title") or data.get("title") or "Без заголовка"
                source = data.get(b"source") or data.get("source") or "unknown"
                generated_at = data.get(b"generated_at") or data.get("generated_at") or ""
                is_published = data.get(b"is_published") in (b"1", "1", True, 1)

                if isinstance(title, bytes):
                    title = title.decode("utf-8", errors="ignore")
                if isinstance(source, bytes):
                    source = source.decode("utf-8", errors="ignore")
                if isinstance(generated_at, bytes):
                    generated_at = generated_at.decode("utf-8", errors="ignore")

                post = {
                    "source": str(source),
                    "title": str(title)[:110] + "..." if len(str(title)) > 110 else str(title),
                    "status": "Опубликовано" if is_published else "Сгенерирован",
                    "generated_at": str(generated_at)
                }
                posts.append(post)
            except Exception:
                continue

        # Сортируем по времени (новые сверху) и берём 10
        posts = sorted(posts, key=lambda x: x["generated_at"], reverse=True)[:10]

        return {"posts": posts}

    except Exception as e:
        print(f"Error in get_recent_posts: {e}")
        return {"posts": [], "error": str(e)}


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница настроек бота"""
    return templates.TemplateResponse("settings.html", {"request": request})


@app.post("/admin/settings")
async def save_settings(data: dict):
    """Сохранение настроек бота"""
    try:
        # Здесь в будущем можно сохранять настройки в Redis или файл
        # Пока просто возвращаем успех
        return {
            "status": "success",
            "message": "Настройки сохранены"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



@app.get("/health", response_model=dict, tags=["system"])
async def health_check(request: Request):
    redis = getattr(request.app.state, "redis", None)
    redis_ok = False
    if redis:
        try:
            redis_ok = await redis.ping()
        except Exception:
            redis_ok = False

    return JSONResponse(
        content={
            "status": "healthy" if redis_ok else "degraded",
            "redis": "connected" if redis_ok else "disconnected",
        },
        status_code=status.HTTP_200_OK if redis_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
