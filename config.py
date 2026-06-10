import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

TELEGRAM_API_ID: str = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE: str = os.getenv("TELEGRAM_PHONE", "")

TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
MORNING_TIME: str = os.getenv("MORNING_TIME", "08:00")
EVENING_TIME: str = os.getenv("EVENING_TIME", "20:00")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_data.db")
TELETHON_SESSION: str = os.getenv("TELETHON_SESSION", "user_session")
