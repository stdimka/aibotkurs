# init_telegram_session.py
"""
Скрипт для первой авторизации в Telethon + получение SESSION_STRING
Запусти один раз для создания сессии.
"""

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from local_settings import API_ID, API_HASH

phone = input("Введите номер телефона (в формате +37377891665): ").strip()

client = TelegramClient('my_session', API_ID, API_HASH)


async def main():
    print("🔐 Подключение к Telegram...")

    await client.connect()

    if not await client.is_user_authorized():
        print("📲 Начинаем авторизацию...")

        await client.send_code_request(phone)
        code = input('Введите код из Telegram: ').strip()

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input('Введите пароль двухфакторной аутентификации: ').strip()
            await client.sign_in(password=password)

        print("✅ Авторизация прошла успешно!")
    else:
        print("✅ Уже был авторизован ранее.")

    # === Получаем SESSION_STRING ===
    session_string = StringSession.save(client.session)

    print("\n" + "=" * 90)
    print("✅ ТВОЙ SESSION_STRING ГОТОВ:")
    print(session_string)
    print("=" * 90)
    print("\nСкопируй всю строку выше и вставь в local_settings.py как:")
    print('SESSION_STRING = "сюда_вставь_строку"')
    print("\nПосле этого можно использовать StringSession в парсере.")

    # Дополнительно: информация об аккаунте
    me = await client.get_me()
    print(f"\n👤 Авторизован как: {me.first_name} (@{me.username})")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
