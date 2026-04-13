"""
app/ai/generator.py
Модуль для генерации постов с помощью AI-провайдеров.
"""
import asyncio
import httpx
from typing import Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ====================== Модели ======================

class GenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=10, max_length=2000)
    tone: str = Field(default="professional")
    max_length: int = Field(default=700, ge=100, le=2000)


class GenerateResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    model: Optional[str] = None


# ====================== Основная функция ======================
async def ai_generate_post(
    title: str,
    summary: str,
    tone: str = "professional",
    max_length: int = 700,
) -> GenerateResponse:
    """
    Генерация поста с поддержкой редактируемого System Prompt из Redis.
    """
    try:
        request = GenerateRequest(title=title, summary=summary, tone=tone, max_length=max_length)
    except ValueError as e:
        logger.error(f"Ошибка валидации запроса: {e}")
        return GenerateResponse(success=False, error=f"Validation error: {e}")

    # ====================== Получение System Prompt ======================
    redis_client = get_sync_redis()
    system_prompt_raw = redis_client.get("settings:system_prompt")

    if system_prompt_raw:
        if isinstance(system_prompt_raw, bytes):
            system_prompt = system_prompt_raw.decode("utf-8")
        else:
            system_prompt = str(system_prompt_raw)
        logger.info("✅ Используется System Prompt из Redis (редактируемый)")
    else:
        system_prompt = """Ты — профессиональный редактор технологического Telegram-канала.
Пиши увлекательно, но по делу. Используй эмодзи умеренно.
Делай акцент на практической пользе и новых возможностях.
Избегай воды и корпоративного стиля. 
Максимум 800 символов."""
        logger.info("✅ Используется дефолтный System Prompt из кода")

    # Подставляем тон
    system_prompt = system_prompt.format(tone=request.tone)

    user_prompt = f"""
Заголовок новости:
{request.title}

Содержание:
{request.summary}

Напиши пост для Telegram-канала. Тон: {request.tone}. Максимальная длина: {request.max_length} символов.
"""

    full_prompt = f"{system_prompt}\n\n{user_prompt}"


    payload = {
        "message": full_prompt,
        "max_tokens": min(request.max_length // 3 + 100, 900),
        "temperature": 0.78,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AIBotKurs/1.0",
    }

    if settings.AI_API_KEY and settings.AI_API_KEY.strip():
        headers["Authorization"] = f"Bearer {settings.AI_API_KEY}"
        logger.info("Используется API ключ для запроса к AI")

    backoff_times = [6, 12, 20, 30, 45]

    for attempt, wait_time in enumerate(backoff_times, 1):
        try:
            logger.info(f"AI запрос (попытка {attempt}/{len(backoff_times)})")

            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(
                    settings.FREE_AI_URL,
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    content = (
                        data.get("generated_text") or
                        data.get("response") or
                        data.get("content") or
                        data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    )

                    if content and isinstance(content, str) and content.strip():
                        logger.info(f"✅ Пост сгенерирован ({len(content)} символов)")
                        return GenerateResponse(
                            success=True,
                            content=content.strip(),
                            model=data.get("model")
                        )

                elif response.status_code == 429:
                    logger.warning(f"Rate limit 429. Ждём {wait_time} сек...")
                    await asyncio.sleep(wait_time)
                    continue

                else:
                    logger.error(f"AI API вернул {response.status_code}: {response.text[:300]}")
                    await asyncio.sleep(3)

        except httpx.TimeoutException:
            logger.warning("Таймаут запроса к AI")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при запросе к AI")
            await asyncio.sleep(3)

    return GenerateResponse(success=False, error="Не удалось сгенерировать пост после нескольких попыток")


def truncate_for_prompt(text: str, max_chars: int = 1600) -> str:
    """Обрезает текст для промпта"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit('.', 1)[0] + "..."
