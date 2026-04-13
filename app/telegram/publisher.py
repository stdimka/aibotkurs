from datetime import datetime
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, MediaCaptionTooLongError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramPublisher:
    """Асинхронный публикатор в Telegram с улучшенной обработкой ошибок"""

    async def publish_post(
            self,
            title: str,
            text: str,
            image_url: str | None = None,
            channel_username: str | None = None,
    ) -> bool:
        """
        Публикует пост в Telegram-канал.
        """
        if channel_username is None:
            channel_username = settings.TG_CHANNEL

        try:
            async with TelegramClient(
                StringSession(settings.TG_SESSION_STR),
                settings.TG_API_ID,
                settings.TG_API_HASH
            ) as client:

                entity = await client.get_entity(channel_username)

                now = datetime.now().strftime("%d.%m.%Y %H:%M")

                # Ограничиваем длину подписи (Telegram имеет лимит)
                full_message = f"**{title}**\n\n{text}\n\n🕒 {now}"
                if len(full_message) > 900:   # оставляем запас
                    full_message = full_message[:897] + "..."

                # Пытаемся отправить с картинкой
                if image_url and image_url.startswith("http"):
                    try:
                        await client.send_file(
                            entity=entity,
                            file=image_url,
                            caption=full_message,
                            parse_mode="md",
                            force_document=False,
                        )
                        logger.info(f"✅ Пост с изображением успешно опубликован в @{channel_username}")
                        return True
                    except Exception as img_err:
                        logger.warning(f"Не удалось отправить изображение {image_url}: {img_err}. Отправляем текстом.")
                        # Если картинка не работает — отправляем только текст
                        await client.send_message(
                            entity=entity,
                            message=full_message,
                            parse_mode="md",
                            link_preview=False,
                        )
                else:
                    # Отправка только текстом
                    await client.send_message(
                        entity=entity,
                        message=full_message,
                        parse_mode="md",
                        link_preview=False,
                    )

                logger.info(f"✅ Пост успешно опубликован в @{channel_username}")
                return True

        except FloodWaitError as e:
            logger.warning(f"FloodWait: ожидание {e.seconds} секунд")
            await asyncio.sleep(e.seconds + 5)
            return False

        except MediaCaptionTooLongError:
            logger.warning("Подпись слишком длинная. Сокращаем...")
            # Сокращаем сообщение
            short_message = full_message[:900] + "..."
            await client.send_message(
                entity=entity,
                message=short_message,
                parse_mode="md",
                link_preview=False,
            )
            logger.info(f"✅ Пост опубликован (сокращённая версия) в @{channel_username}")
            return True

        except ChatWriteForbiddenError:
            logger.error(f"Нет прав на публикацию в @{channel_username}")
            return False

        except Exception as e:
            logger.exception(f"❌ Ошибка публикации в @{channel_username}")
            return False


# Singleton
telegram_publisher = TelegramPublisher()
