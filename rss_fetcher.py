"""Fetches news from RSS/Atom feeds."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import aiohttp
import feedparser

logger = logging.getLogger(__name__)

HOURS_BACK = 24


@dataclass
class NewsItem:
    title: str
    summary: str
    url: str
    source_name: str
    source_category: str | None
    published: datetime


def _parse_entry_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _clean_html(text: str) -> str:
    """Strip basic HTML tags."""
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


async def fetch_rss(url: str, source_name: str, source_category: str | None) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)
    items: list[NewsItem] = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                content = await resp.read()

        feed = feedparser.parse(content)

        for entry in feed.entries:
            pub = _parse_entry_date(entry)
            if pub and pub < cutoff:
                continue

            title = getattr(entry, "title", "Без заголовка")
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            link = getattr(entry, "link", "")

            items.append(NewsItem(
                title=_clean_html(title),
                summary=_clean_html(summary),
                url=link,
                source_name=source_name,
                source_category=source_category,
                published=pub or datetime.now(timezone.utc),
            ))

    except Exception as e:
        logger.warning(f"RSS fetch error for {url}: {e}")

    return items


async def fetch_all_rss(sources: list[dict]) -> list[NewsItem]:
    tasks = [
        fetch_rss(s["url"], s["name"], s.get("category"))
        for s in sources
        if s.get("source_type") == "rss"
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_items: list[NewsItem] = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)
    return all_items
