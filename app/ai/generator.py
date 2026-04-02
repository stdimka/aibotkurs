"""
app/ai/generator.py
Модуль для генерации постов с помощью AI-провайдеров.
"""
import asyncio
import httpx
import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ====================== Модели ======================

class GenerateRequest(BaseModel):
    """Запрос к AI-провайдеру."""
    title: str = Field(..., min_length=1, max_length=500, description="Заголовок новости")
    summary: str = Field(..., min_length=10, max_length=2000, description="Краткое содержание")
    tone: str = Field(default="professional", description="Стиль поста: professional, casual, humorous")
    max_length: int = Field(default=500, ge=100, le=2000, description="Максимальная длина поста")


class GenerateResponse(BaseModel):
    """Ответ от AI-провайдера."""
    success: bool = Field(..., description="Успешно ли сгенерировано")
    content: Optional[str] = Field(default=None, description="Сгенерированный текст")
    error: Optional[str] = Field(default=None, description="Текст ошибки")
    tokens_used: Optional[int] = Field(default=None, description="Использовано токенов")
    model: Optional[str] = Field(default=None, description="Использованная модель")

    # 🔹 Добавлено поле для совместимости с кодом генерации
    original_title: Optional[str] = Field(default=None, description="Оригинальный заголовок новости")

# ====================== Промпты ======================

SYSTEM_PROMPT = """Ты — профессиональный редактор новостного Telegram-канала.
Твоя задача: создать краткий, увлекательный пост на основе новости.

Требования:
1. Длина: 150-400 слов
2. Стиль: {tone}, без воды и клише
3. Структура: 
   - Цепляющий первый абзац (лид)
   - Основная суть новости (факты, цифры)
   - Контекст или почему это важно
   - Призыв к действию или вопрос аудитории (опционально)
4. Форматирование: используй **жирный** для акцентов, но без избытка
5. Язык: русский, грамотный, без канцеляризмов

Не добавляй заголовок — он уже есть. Не используй эмодзи, если не указано иное.
"""

USER_PROMPT_TEMPLATE = """
Заголовок: {title}

Содержание:
{summary}

Создай пост для Telegram-канала. Тон: {tone}. Макс. длина: {max_length} символов.
"""


# ====================== Основная функция ======================

# app/ai/generator.py

async def ai_generate_post(
        title: str,
        summary: str,
        tone: str = "professional",
        max_length: int = 500,
        timeout: float = 30.0,
        retries: int = 3,
) -> GenerateResponse:
    """
    Генерация поста через AI-провайдер (apifreellm.com compatible).
    """
    # Валидация входных данных
    try:
        request = GenerateRequest(
            title=title,
            summary=summary,
            tone=tone,
            max_length=max_length
        )
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return GenerateResponse(success=False, error=f"Validation: {e}")

    # Формируем промпт
    system_prompt = SYSTEM_PROMPT.format(tone=request.tone)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=request.title,
        summary=request.summary,
        tone=request.tone,
        max_length=request.max_length
    )

    # 🔹 Формат для apifreellm.com: один параметр "message"
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    payload = {
        "message": full_prompt,  # ← ключевое: один строковый параметр
        "max_tokens": min(request.max_length // 4, 1000),
        "temperature": 0.7,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "aibotkurs/1.0",
    }

    # Authorization только если есть ключ
    if settings.ai_api_key:
        headers["Authorization"] = f"Bearer {settings.ai_api_key}"

    last_error = None

    for attempt in range(retries):
        try:
            logger.info(f"AI запрос (попытка {attempt + 1}/{retries})")

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url=settings.free_ai_url,
                    headers=headers,
                    json=payload
                )

                logger.debug(f"AI API status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    # 🔹 Парсинг ответа apifreellm.com
                    # Пробуем разные возможные поля
                    content = (
                            data.get("generated_text") or
                            data.get("response") or
                            data.get("content") or
                            data.get("choices", [{}])[0].get("text") or
                            data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    )

                    if content and isinstance(content, str) and content.strip():
                        logger.info(f"✅ Пост сгенерирован ({len(content)} симв.)")
                        return GenerateResponse(
                            success=True,
                            content=content.strip(),
                            tokens_used=data.get("usage", {}).get("total_tokens"),
                            model=data.get("model", "unknown")
                        )
                    else:
                        logger.warning("AI вернул пустой или некорректный контент")
                        last_error = "Empty/invalid response from AI"

                elif response.status_code == 401:
                    logger.error("❌ Ошибка авторизации AI API")
                    return GenerateResponse(success=False, error="Auth failed: check ai_api_key")

                elif response.status_code == 400:
                    error_detail = response.json().get("error", "Bad request")
                    logger.error(f"❌ Ошибка в запросе к AI: {error_detail}")
                    # Не повторяем при 400 — это ошибка формата, а не временная
                    return GenerateResponse(success=False, error=f"Bad request: {error_detail}")

                elif response.status_code == 429:
                    logger.warning("⚠️ Rate limit, ждём...")
                    await asyncio.sleep(2 ** attempt)
                    continue

                elif response.status_code >= 500:
                    logger.warning(f"⚠️ Ошибка сервера ({response.status_code}), повтор...")
                    await asyncio.sleep(1)
                    continue

                else:
                    error_text = response.text[:200] if response.text else "No details"
                    logger.error(f"❌ AI API error ({response.status_code}): {error_text}")
                    last_error = f"API {response.status_code}: {error_text}"
                    break

        except httpx.TimeoutException:
            logger.warning(f"⏱ Таймаут (попытка {attempt + 1})")
            last_error = "Timeout"
            await asyncio.sleep(1)
            continue

        except httpx.ConnectError as e:
            logger.warning(f"🔌 Ошибка подключения: {e}")
            last_error = f"Connection: {e}"
            await asyncio.sleep(1)
            continue

        except Exception as e:
            logger.exception(f"❌ Неожиданная ошибка")
            last_error = f"Unexpected: {e}"
            break

    logger.error(f"❌ Не удалось после {retries} попыток")
    return GenerateResponse(success=False, error=last_error or "Unknown error")


# ====================== Утилиты ======================

def truncate_for_prompt(text: str, max_chars: int = 1500) -> str:
    """
    Обрезает текст до безопасной длины для промпта.

    Args:
        text: Исходный текст
        max_chars: Максимальное количество символов

    Returns:
        Обрезанный текст с индикатором, если было усечение
    """
    if len(text) <= max_chars:
        return text

    # Обрезаем по последнему предложению, чтобы не рвать мысль
    truncated = text[:max_chars].rsplit('.', 1)[0]
    return truncated + "..." if truncated else text[:max_chars] + "..."


def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    """
    Грубая оценка количества токенов по тексту.

    Note: Для точного подсчёта используйте токенизатор вашей модели.
    """
    return max(1, int(len(text) / chars_per_token))