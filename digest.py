"""Assembles morning and evening digests. Uses HTML parse mode."""

import html
import logging
from datetime import date

from apple_calendar import get_today_events, get_tomorrow_events
from apple_reminders import get_today_reminders
from database import get_active_sources
from rss_fetcher import fetch_all_rss
from telegram_channels import fetch_all_telegram
from summarizer import summarize_news

logger = logging.getLogger(__name__)

SEP = "─" * 28


def e(text: str) -> str:
    """Escape text for Telegram HTML."""
    return html.escape(str(text))


def _format_events(events) -> str:
    if not events:
        return "<i>Событий нет</i>"
    lines = []
    for ev in events:
        if ev.all_day:
            lines.append(f"• {e(ev.title)} <i>(весь день)</i>")
        else:
            lines.append(f"• <code>{e(ev.start_time)}–{e(ev.end_time)}</code> {e(ev.title)}")
    return "\n".join(lines)


def _format_reminders(reminders) -> str:
    if not reminders:
        return "<i>Напоминаний нет</i>"
    lines = []
    for r in reminders:
        mark = " ❗" if r.priority >= 1 else ""
        lines.append(f"• <code>{e(r.due_time)}</code> {e(r.title)}{mark}")
    return "\n".join(lines)


def _format_news_summary(summaries) -> str:
    if not summaries:
        return "<i>Источники новостей не настроены или нет новостей за 24 часа</i>"
    parts = []
    for s in summaries:
        parts.append(f"<b>{e(s.category)}</b>\n{s.summary}")
    return "\n\n".join(parts)


async def build_morning_digest() -> str:
    today_str = date.today().strftime("%d.%m.%Y")

    events = get_today_events()
    reminders = get_today_reminders()
    sources = get_active_sources()
    rss_items = await fetch_all_rss(sources)
    tg_items = await fetch_all_telegram(sources)
    all_news = rss_items + tg_items
    summaries = await summarize_news(all_news)

    news_block = _format_news_summary(summaries)
    sources_count = len(sources)
    news_count = len(all_news)

    return (
        f"🌅 <b>Доброе утро! Дайджест на {e(today_str)}</b>\n"
        f"{SEP}\n\n"
        f"📅 <b>Календарь на сегодня</b>\n"
        f"{_format_events(events)}\n\n"
        f"✅ <b>Напоминания на сегодня</b>\n"
        f"{_format_reminders(reminders)}\n\n"
        f"📰 <b>Новости за прошедшие 24 часа</b>\n"
        f"<i>Источников: {sources_count} | Материалов: {news_count}</i>\n\n"
        f"{news_block}"
    )


async def build_evening_digest() -> str:
    today_str = date.today().strftime("%d.%m.%Y")

    tomorrow_events = get_tomorrow_events()
    sources = get_active_sources()
    rss_items = await fetch_all_rss(sources)
    tg_items = await fetch_all_telegram(sources)
    all_news = rss_items + tg_items
    summaries = await summarize_news(all_news)

    news_block = _format_news_summary(summaries)

    return (
        f"🌆 <b>Вечерний дайджест — {e(today_str)}</b>\n"
        f"{SEP}\n\n"
        f"📅 <b>События на завтра</b>\n"
        f"{_format_events(tomorrow_events)}\n\n"
        f"📰 <b>Главное за день</b>\n\n"
        f"{news_block}"
    )


def split_message(text: str, max_len: int = 4000) -> list[str]:
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
