"""Fetches messages from Telegram channels via Telethon (user account API)."""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

HOURS_BACK = 24


@dataclass
class TelegramPost:
    text: str
    url: str
    source_name: str
    source_category: str | None
    published: datetime


async def fetch_telegram_channel(
    client,
    channel: str,
    source_name: str,
    source_category: str | None,
) -> list[TelegramPost]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)
    posts: list[TelegramPost] = []

    try:
        entity = await client.get_entity(channel)
        async for message in client.iter_messages(entity, limit=50):
            if message.date < cutoff:
                break
            if not message.text or len(message.text.strip()) < 20:
                continue

            chan_username = getattr(entity, "username", None)
            if chan_username:
                url = f"https://t.me/{chan_username}/{message.id}"
            else:
                url = f"https://t.me/c/{entity.id}/{message.id}"

            posts.append(TelegramPost(
                text=message.text[:800],
                url=url,
                source_name=source_name,
                source_category=source_category,
                published=message.date,
            ))

    except Exception as e:
        logger.warning(f"Telegram fetch error for {channel}: {e}")

    return posts


async def fetch_all_telegram(sources: list[dict]) -> list[TelegramPost]:
    from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TELETHON_SESSION

    tg_sources = [s for s in sources if s.get("source_type") == "telegram"]
    if not tg_sources:
        return []

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.warning("Telegram API credentials not configured — skipping TG channels")
        return []

    session_file = f"{TELETHON_SESSION}.session"
    if not os.path.exists(session_file):
        logger.warning("Telethon session not found — run setup_telethon.py first")
        return []

    try:
        from telethon import TelegramClient

        client = TelegramClient(TELETHON_SESSION, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            logger.warning("Telethon session expired — run setup_telethon.py again")
            await client.disconnect()
            return []

        all_posts: list[TelegramPost] = []
        for src in tg_sources:
            posts = await fetch_telegram_channel(
                client, src["url"], src["name"], src.get("category")
            )
            all_posts.extend(posts)

        await client.disconnect()
        return all_posts

    except Exception as e:
        logger.warning(f"Telethon error: {e}")
        return []
