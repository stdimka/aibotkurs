import time
import httpx
from app.config import settings
from app.schemas.generate import GenerateResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

FREE_AI_URL = "https://apifreellm.com/api/v1/chat"


def ai_generate_post(title: str, summary: str, max_retries: int = 3) -> GenerateResponse:
    """
    Возвращает (новый_заголовок, сгенерированный_пост)
    """
    if not title or not summary:
        raise ValueError("Title и summary обязательны")

    prompt = (
        f"Сделай яркий, лаконичный и интересный пост для Telegram-канала на основе новости.\n"
        f"Заголовок новости: {title}\n"
        f"Краткое содержание: {summary}\n\n"
        "Требования:\n"
        "• 5-7 предложений максимум\n"
        "• Добавь 2–4 релевантных emoji\n"
        "• Стиль живой, как у хорошего Telegram-канала\n"
        "• Не используй слова «дорогие друзья» и «новость дня»\n"
        'В ответе отдели новый заголовок от текста тройным символом |||'
    )

    payload = {"message": prompt}

    attempt = 0

    while attempt <= max_retries:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    FREE_AI_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.ai_api_key}",
                    },
                )
                response.raise_for_status()
                data = response.json()

                generated_text = data.get("response") or data.get("text") or str(data)

                lines = generated_text.strip().split("|||", 1)
                new_title = lines[0].strip("# *").strip() if lines else title
                post_text = lines[1].strip() if len(lines) > 1 else generated_text

                logger.info(f"AI успешно сгенерировал пост для: {title[:50]}...")

                return GenerateResponse(
                    original_title=title,
                    new_title=new_title,
                    generated_post=post_text,
                )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            if status_code == 429 and attempt < max_retries:
                attempt += 1
                logger.warning(
                    f"Получен 429 (rate limit). Попытка {attempt}/{max_retries}. "
                    "Повтор через 30 секунд..."
                )
                time.sleep(30)
                logger.warning(f"Попытка #{attempt+1}: запуск...")
                continue

            logger.error(f"AI API error {status_code}: {e.response.text}")
            raise

        except Exception:
            logger.exception("Неизвестная ошибка при генерации AI")
            raise

    raise RuntimeError("Превышено максимальное количество попыток при 429")


if __name__ == "__main__":
    params = {
      "title": "Фреймворк FastAPI выходит на лидирующие позиции",
      "summary": "Фреймворк FastAPI стремительно выходит на лидирующие позиции среди инструментов для разработки веб-приложений на Python."
    }
    print(ai_generate_post(**params))
