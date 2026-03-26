# app/telegram/publisher.py
from datetime import datetime
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, PeerFloodError

from app.telegram.client import get_telegram_client
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class TelegramPublisher:
    async def publish_post(self, title: str, text: str, channel_username: str | None = None) -> bool:
        if channel_username is None:
            channel_username = settings.target_channel

        try:
            client = await get_telegram_client()
            entity = await client.get_entity(channel_username)

            now = datetime.now().strftime("%d.%m %H:%M")

            message = f"**{title}**\n\n{text}\n\n🕒 {now}"

            await client.send_message(
                entity,
                message,
                parse_mode="md",
                link_preview=False
            )

            logger.info(f"✅ Пост опубликован в @{channel_username}")
            return True

        except FloodWaitError as e:
            logger.warning(f"FloodWait при публикации: {e.seconds} сек")
            await asyncio.sleep(e.seconds + 15)
            return False
        except ChatWriteForbiddenError:
            logger.error(f"Нет прав писать в @{channel_username}")
            return False
        except Exception as e:
            logger.exception("Ошибка публикации поста")
            return False


telegram_publisher = TelegramPublisher()
