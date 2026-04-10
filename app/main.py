from contextlib import asynccontextmanager
from typing import AsyncGenerator
import json

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import init_redis_pool
from app.utils.logging import get_logger
from app.utils.initialization import initialize_default_settings
from app.redis_sync import get_sync_redis
from app.config import settings

logger = get_logger(__name__)  # ← Добавили глобальный logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Запуск приложения aibot ...")

    redis_initialized = False
    try:
        redis_pool = await init_redis_pool()
        app.state.redis = redis_pool
        redis_initialized = True

        await initialize_default_settings(redis_pool)

        # Инициализация дефолтных промпта и ключевых слов
        await initialize_default_prompt_and_keywords(redis_pool)

        logger.info("Дефолтные настройки проверены / инициализированы")
    except Exception as e:
        logger.error(f"Ошибка инициализации Redis: {e}")
        app.state.redis = None

    yield

    logger.info("Остановка приложения aibot ...")
    if redis_initialized and hasattr(app.state, "redis"):
        try:
            redis = app.state.redis
            await redis.close()
            await redis.connection_pool.disconnect()
        except Exception as e:
            logger.warning(f"Ошибка закрытия Redis: {e}")

    logger.info("Приложение остановлено")


app = FastAPI(
    title="AI News Telegram Bot",
    description="Автоматизированный новостной канал с генерацией постов через ИИ",
    lifespan=lifespan
)

# ====================== РОУТЕРЫ ======================
from app.api.v1 import (
    keywords, site_sources, tg_sources, posts,
    filtered_posts, history, generate
)

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
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/tg_sources", response_class=HTMLResponse)
async def tg_sources_page(request: Request):
    return templates.TemplateResponse("tg_sources.html", {"request": request})


@app.get("/site_sources", response_class=HTMLResponse)
async def site_sources_page(request: Request):
    return templates.TemplateResponse("site_sources.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


# Сохранение настроек (включая System Prompt)
@app.post("/admin/settings")
async def save_settings(data: dict):
    try:
        redis = get_sync_redis()

        for key, value in data.items():
            if key == "keywords" and isinstance(value, list):
                redis.set("settings:keywords", json.dumps(value))
            else:
                redis.set(f"settings:{key}", str(value))

        return {
            "status": "success",
            "message": "Настройки успешно сохранены"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка сохранения настроек: {str(e)}"
        }


@app.post("/admin/run_pipeline")
async def trigger_pipeline(request: Request):
    lang = request.query_params.get("lang", "ru")

    try:
        from celery_app import celery_app
        celery_app.send_task("run_pipeline_task")

        if lang == "en":
            message = "Pipeline successfully launched in the background!"
        else:
            message = "Пайплайн успешно запущен в фоне."

        return {
            "status": "success",
            "message": message
        }
    except Exception as e:
        if lang == "en":
            error_msg = f"Error launching pipeline: {str(e)}"
        else:
            error_msg = f"Ошибка запуска пайплайна: {str(e)}"

        return {
            "status": "error",
            "message": error_msg
        }


@app.get("/admin/recent_posts")
async def get_recent_posts():
    try:
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

        posts = sorted(posts, key=lambda x: x["generated_at"], reverse=True)[:10]
        return {"posts": posts}

    except Exception as e:
        print(f"Error in get_recent_posts: {e}")
        return {"posts": [], "error": str(e)}


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


# ====================== ИНИЦИАЛИЗАЦИЯ ДЕФОЛТНЫХ НАСТРОЕК ======================
async def initialize_default_prompt_and_keywords(redis_pool):
    """Надёжная инициализация дефолтных промпта и ключевых слов"""
    try:
        redis = get_sync_redis()   # используем sync клиент

        # === Ключевые слова ===
        if not redis.exists("settings:keywords"):
            redis.set("settings:keywords", json.dumps(settings.keywords))
            logger.info(f"✅ Инициализированы дефолтные ключевые слова ({len(settings.keywords)} шт.)")
        else:
            logger.info("Ключевые слова уже существуют в Redis")

        # === System Prompt ===
        if not redis.exists("settings:system_prompt"):
            default_prompt = """Ты — профессиональный редактор технологического Telegram-канала.
Пиши увлекательно, но по делу. Используй эмодзи умеренно.
Делай акцент на практической пользе и новых возможностях.
Избегай воды и корпоративного стиля. 
Максимум 800 символов."""

            redis.set("settings:system_prompt", default_prompt)
            logger.info("✅ Инициализирован дефолтный System Prompt")
        else:
            logger.info("System Prompt уже существует в Redis")

    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации дефолтных настроек: {e}")


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)