"""
app/ai/generator.py
Модуль для генерации постов с помощью AI-провайдеров.
"""
import asyncio
import httpx
import json
from typing import Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ====================== Модели ======================

class GenerateRequest(BaseModel):
    """Запрос к AI-провайдеру."""
    title: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=10, max_length=2000)
    tone: str = Field(default="professional")
    max_length: int = Field(default=600, ge=100, le=2000)


class GenerateResponse(BaseModel):
    """Ответ от AI-провайдера."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    model: Optional[str] = None


# ====================== Промпты ======================

SYSTEM_PROMPT = """Ты — профессиональный редактор новостного Telegram-канала.
Создавай увлекательные, лаконичные и грамотные посты.

Правила:
- Длина: 350–650 символов
- Стиль: {tone}, живой, без канцеляризмов
- Первый абзац должен цеплять внимание
- Используй факты и цифры
- Можно использовать **жирный** для акцентов
- Не добавляй заголовок — он уже есть
- Не используй эмодзи, если не указано явно"""

USER_PROMPT_TEMPLATE = """
Заголовок новости:
{title}

Содержание:
{summary}

Напиши пост для Telegram-канала. Тон: {tone}. Максимальная длина: {max_length} символов.
"""


# ====================== Основная функция ======================

async def ai_generate_post(
    title: str,
    summary: str,
    tone: str = "professional",
    max_length: int = 600,
) -> GenerateResponse:
    """
    Генерация поста с улучшенной обработкой rate limit и ошибок.
    """
    try:
        request = GenerateRequest(title=title, summary=summary, tone=tone, max_length=max_length)
    except ValueError as e:
        logger.error(f"Ошибка валидации запроса: {e}")
        return GenerateResponse(success=False, error=f"Validation error: {e}")

    system_prompt = SYSTEM_PROMPT.format(tone=request.tone)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=request.title,
        summary=request.summary,
        tone=request.tone,
        max_length=request.max_length
    )

    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    payload = {
        "message": full_prompt,
        "max_tokens": min(request.max_length // 3, 800),
        "temperature": 0.75,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AIBotKurs/1.0",
    }

    # Добавляем API ключ, если он есть
    if settings.AI_API_KEY and settings.AI_API_KEY.strip():
        headers["Authorization"] = f"Bearer {settings.AI_API_KEY}"
        logger.info("Используется API ключ для запроса к AI")
    else:
        logger.info("API ключ не указан, запрос без авторизации")

    # Задержки при rate limit (экспоненциальный backoff)
    backoff_times = [6, 12, 20, 30, 45]

    for attempt, wait_time in enumerate(backoff_times, 1):
        try:
            logger.info(f"AI запрос (попытка {attempt}/{len(backoff_times)})")

            async with httpx.AsyncClient(timeout=35.0) as client:
                response = await client.post(
                    settings.free_ai_url,
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

                elif response.status_code == 401:
                    logger.error("401 Unauthorized — проверь правильность AI_API_KEY")
                    return GenerateResponse(success=False, error="Authorization failed - check AI_API_KEY")

                elif response.status_code >= 500:
                    logger.warning(f"Ошибка сервера {response.status_code}. Повторяем...")
                    await asyncio.sleep(3)
                    continue

                else:
                    logger.error(f"AI API вернул {response.status_code}: {response.text[:200]}")
                    await asyncio.sleep(2)

        except httpx.TimeoutException:
            logger.warning("Таймаут запроса к AI")
            await asyncio.sleep(4)
            continue
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при запросе к AI")
            await asyncio.sleep(3)


# ====================== Утилита ======================

def truncate_for_prompt(text: str, max_chars: int = 1600) -> str:
    """Обрезает текст для промпта"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit('.', 1)[0] + "..."
