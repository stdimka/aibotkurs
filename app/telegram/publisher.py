from datetime import datetime
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChatWriteForbiddenError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramPublisher:
    """Асинхронный публикатор в Telegram"""

    async def publish_post(self, title: str, text: str, channel_username: str | None = None) -> bool:
        """
        Публикует пост в Telegram-канал.
        Возвращает True при успехе.
        """
        if channel_username is None:
            channel_username = settings.tg_channel

        try:
            async with TelegramClient(
                StringSession(settings.tg_session_str),
                settings.tg_api_id,
                settings.tg_api_hash
            ) as client:

                entity = await client.get_entity(channel_username)

                now = datetime.now().strftime("%d.%m.%Y %H:%M")

                full_message = f"**{title}**\n\n{text}\n\n🕒 {now}"

                await client.send_message(
                    entity=entity,
                    message=full_message,
                    parse_mode="md",
                    link_preview=False
                )

                logger.info(f"✅ Пост успешно опубликован в @{channel_username}")
                return True

        except FloodWaitError as e:
            logger.warning(f"FloodWait при публикации: ожидание {e.seconds} секунд")
            await asyncio.sleep(e.seconds + 10)
            return False
        except ChatWriteForbiddenError:
            logger.error(f"❌ Нет прав на публикацию в канале @{channel_username}")
            return False
        except Exception as e:
            logger.exception(f"❌ Ошибка публикации в @{channel_username}")
            return False


# Singleton
telegram_publisher = TelegramPublisher()