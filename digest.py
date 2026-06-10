"""Assembles morning and evening digests."""

import logging
from datetime import date

from apple_calendar import get_today_events, get_tomorrow_events
from apple_reminders import get_today_reminders
from database import get_active_sources
from rss_fetcher import fetch_all_rss
from telegram_channels import fetch_all_telegram
from summarizer import summarize_news

logger = logging.getLogger(__name__)

CATEGORY_ICONS = {
    "Технологии": "💻",
    "Политика": "🏛",
    "Экономика": "💰",
    "Мир": "🌍",
    "Наука": "🔬",
    "Спорт": "⚽",
    "Культура": "🎭",
    "Прочее": "📌",
}


def _icon(category: str) -> str:
    return CATEGORY_ICONS.get(category, "📰")


def _format_events(events) -> str:
    if not events:
        return "_Событий нет_"
    lines = []
    for e in events:
        if e.all_day:
            lines.append(f"• {e.title} *(весь день)*")
        else:
            lines.append(f"• `{e.start_time}–{e.end_time}` {e.title}")
    return "\n".join(lines)


def _format_reminders(reminders) -> str:
    if not reminders:
        return "_Напоминаний нет_"
    lines = []
    for r in reminders:
        priority_mark = " ❗" if r.priority >= 1 else ""
        lines.append(f"• `{r.due_time}` {r.title}{priority_mark}")
    return "\n".join(lines)


def _format_news_summary(summaries) -> str:
    if not summaries:
        return "_Источники новостей не настроены или нет новостей за 24 часа_"
    parts = []
    for s in summaries:
        icon = _icon(s.category)
        parts.append(f"{icon} *{s.category}*\n{s.summary}")
    return "\n\n".join(parts)


async def build_morning_digest() -> str:
    today_str = date.today().strftime("%d.%m.%Y")

    # Calendar
    events = get_today_events()
    # Reminders
    reminders = get_today_reminders()
    # News
    sources = get_active_sources()
    rss_items = await fetch_all_rss(sources)
    tg_items = await fetch_all_telegram(sources)
    all_news = rss_items + tg_items
    summaries = await summarize_news(all_news)

    news_block = _format_news_summary(summaries)
    sources_count = len(sources)
    news_count = len(all_news)

    text = (
        f"🌅 *Доброе утро! Дайджест на {today_str}*\n"
        f"{'─' * 30}\n\n"
        f"📅 *Календарь на сегодня*\n"
        f"{_format_events(events)}\n\n"
        f"✅ *Напоминания на сегодня*\n"
        f"{_format_reminders(reminders)}\n\n"
        f"📰 *Новости за прошедшие 24 часа*\n"
        f"_Источников: {sources_count} | Материалов: {news_count}_\n\n"
        f"{news_block}"
    )
    return text


async def build_evening_digest() -> str:
    today_str = date.today().strftime("%d.%m.%Y")

    tomorrow_events = get_tomorrow_events()
    sources = get_active_sources()
    rss_items = await fetch_all_rss(sources)
    tg_items = await fetch_all_telegram(sources)
    all_news = rss_items + tg_items
    summaries = await summarize_news(all_news)

    news_block = _format_news_summary(summaries)

    text = (
        f"🌆 *Вечерний дайджест — {today_str}*\n"
        f"{'─' * 30}\n\n"
        f"📅 *События на завтра*\n"
        f"{_format_events(tomorrow_events)}\n\n"
        f"📰 *Главное за день*\n\n"
        f"{news_block}"
    )
    return text


def split_message(text: str, max_len: int = 4000) -> list[str]:
    """Split long text into Telegram-safe chunks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
