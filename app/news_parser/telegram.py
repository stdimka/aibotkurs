# app/news_parser/telegram.py
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def parse_tg_channel(channel: str, limit: int | None = None):
    """
    Асинхронный парсер Telegram-канала
    """
    if limit is None:
        limit = settings.MAX_NEWS_PER_SOURCE_PER_RUN

    try:
        async with TelegramClient(
                StringSession(settings.TG_SESSION_STR),
                settings.TG_API_ID,
                settings.TG_API_HASH
        ) as client:

            logger.info(f"Начинаем парсинг канала {channel} (limit={limit})")

            posts = []
            async for msg in client.iter_messages(channel, limit=limit):
                if not msg.text or len(msg.text.strip()) < 10:
                    continue

                post = {
                    "title": msg.text.split("\n")[0][:200] if msg.text else "Без заголовка",
                    "url": f"https://t.me/{channel}/{msg.id}",
                    "summary": msg.text[:800],  # ограничиваем размер
                    "raw_text": msg.text,
                    "published_at": msg.date.isoformat(),
                    "source": f"tg_{channel.strip('@')}",
                    "tg_message_id": msg.id,
                }
                posts.append(post)

            logger.info(f"Успешно получено {len(posts)} постов из @{channel}")
            return posts

    except FloodWaitError as e:
        logger.warning(f"FloodWaitError: нужно подождать {e.seconds} секунд")
        await asyncio.sleep(e.seconds + 5)
        return []
    except Exception as e:
        logger.exception(f"Ошибка при парсинге канала {channel}")
        return []


# Для теста
if __name__ == "__main__":
    async def test():
        CHANNEL = "@techmedia"  # замени на свой канал
        posts = await parse_tg_channel(CHANNEL, limit=5)

        for post in posts:
            print("Title:", post['title'])
            print("Link:", post['url'])
            print("Summary:", post.get('summary')[:150] + "..." if post.get('summary') else "")
            print("-" * 60)


    asyncio.run(test())
