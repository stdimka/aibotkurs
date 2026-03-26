# app/telegram/client.py
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

telegram_client: TelegramClient | None = None


async def init_telegram_client() -> TelegramClient:
    """Инициализация Telethon клиента (вызывается один раз при старте)"""
    global telegram_client

    if telegram_client is not None:
        return telegram_client

    logger.info("🚀 Инициализация Telethon клиента...")

    client = TelegramClient(
        session="my_session",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():
        logger.warning("⚠️ Требуется авторизация Telethon")
        phone = input("Введите номер телефона (+373...): ")

        await client.send_code_request(phone)
        code = input("Введите код из Telegram: ")

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("Введите 2FA пароль: ")
            await client.sign_in(password=password)

        logger.info("✅ Авторизация Telethon завершена")

    telegram_client = client
    logger.info("✅ Telethon клиент готов к работе")
    return client


async def get_telegram_client() -> TelegramClient:
    """Получить клиент из задач и парсеров"""
    global telegram_client
    if telegram_client is None or not telegram_client.is_connected():
        telegram_client = await init_telegram_client()
    return telegram_client


async def close_telegram_client():
    """Закрытие клиента при остановке приложения"""
    global telegram_client
    if telegram_client:
        try:
            await telegram_client.disconnect()
            logger.info("Telethon клиент отключён")
        except Exception as e:
            logger.warning(f"Ошибка отключения Telethon: {e}")
        telegram_client = None
