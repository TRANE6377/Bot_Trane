"""
One-time setup script to authenticate with Telegram user account (Telethon).
Run this ONCE before starting the bot if you want to read Telegram channels.

Usage:
    python setup_telethon.py
"""

import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")
SESSION = os.getenv("TELETHON_SESSION", "user_session")


async def main():
    if not API_ID or not API_HASH:
        print("❌ TELEGRAM_API_ID и TELEGRAM_API_HASH не заданы в .env")
        print("   Получи их на https://my.telegram.org/apps")
        return

    try:
        from telethon import TelegramClient
    except ImportError:
        print("❌ Установи telethon: pip install telethon")
        return

    client = TelegramClient(SESSION, int(API_ID), API_HASH)

    print("📱 Подключение к Telegram...")
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Уже авторизован как {me.first_name} (@{me.username})")
        await client.disconnect()
        return

    phone = PHONE or input("Введи номер телефона (+7...): ").strip()
    await client.send_code_request(phone)
    code = input("Введи код из Telegram: ").strip()

    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if "two" in str(e).lower() or "password" in str(e).lower():
            password = input("Введи пароль двухфакторной аутентификации: ").strip()
            await client.sign_in(password=password)
        else:
            raise

    me = await client.get_me()
    print(f"✅ Успешно авторизован как {me.first_name} (@{me.username})")
    print(f"📁 Сессия сохранена в файл: {SESSION}.session")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
