# app/news_parser/telegram.py
from telethon.errors import FloodWaitError, ChannelPrivateError
import asyncio

from app.telegram.client import get_telegram_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramParser:
    async def parse_channel(self, channel_username: str, limit: int = 15, min_id: int | None = None):
        client = await get_telegram_client()

        try:
            entity = await client.get_entity(channel_username)

            kwargs = {"limit": limit}
            if min_id:
                kwargs["min_id"] = min_id

            posts = []
            async for message in client.iter_messages(entity, **kwargs):
                if not message.text or len(message.text.strip()) < 15:
                    continue

                post = {
                    "title": message.text.split("\n")[0][:250],
                    "url": f"https://t.me/{channel_username}/{message.id}",
                    "summary": message.text[:500],
                    "source": f"tg_{channel_username}",
                    "published_at": message.date.isoformat(),
                    "raw_text": message.text,
                    "tg_message_id": message.id,
                }
                posts.append(post)

            logger.info(f"📥 @{channel_username} → получено {len(posts)} сообщений")
            return posts

        except FloodWaitError as e:
            logger.warning(f"FloodWait @{channel_username}: {e.seconds} сек.")
            await asyncio.sleep(e.seconds + 10)
            return []
        except Exception as e:
            logger.exception(f"Ошибка парсинга @{channel_username}")
            return []


telegram_parser = TelegramParser()
