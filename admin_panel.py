"""Telegram admin panel — inline keyboard menu for managing the bot."""

import logging
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import OWNER_ID
from database import (
    get_all_sources,
    add_source,
    delete_source,
    toggle_source,
    get_source,
    get_setting,
    set_setting,
)

logger = logging.getLogger(__name__)

# ── State keys stored in context.user_data ─────────────────────────────────
STATE = "admin_state"
PENDING_TYPE = "pending_source_type"  # 'rss' | 'telegram'
PENDING_URL = "pending_source_url"

# State values
S_IDLE = None
S_WAIT_URL = "wait_url"
S_WAIT_NAME = "wait_name"
S_WAIT_MORNING = "wait_morning"
S_WAIT_EVENING = "wait_evening"


def _owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if uid != OWNER_ID:
            if update.message:
                await update.message.reply_text("⛔ Нет доступа.")
            return
        return await func(update, context)
    return wrapper


# ── Keyboards ───────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📰 Источники новостей", callback_data="admin_sources")],
        [InlineKeyboardButton("⏰ Расписание", callback_data="admin_schedule")],
        [
            InlineKeyboardButton("🌅 Тест утреннего", callback_data="admin_test_morning"),
            InlineKeyboardButton("🌆 Тест вечернего", callback_data="admin_test_evening"),
        ],
    ])


def sources_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ RSS / Сайт", callback_data="admin_add_rss"),
            InlineKeyboardButton("➕ Telegram-канал", callback_data="admin_add_tg"),
        ],
        [InlineKeyboardButton("📋 Список источников", callback_data="admin_list_sources")],
        [InlineKeyboardButton("◀ Назад", callback_data="admin_menu")],
    ])


def schedule_keyboard() -> InlineKeyboardMarkup:
    morning = get_setting("morning_time", "08:00")
    evening = get_setting("evening_time", "20:00")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌅 Утро: {morning}", callback_data="admin_set_morning")],
        [InlineKeyboardButton(f"🌆 Вечер: {evening}", callback_data="admin_set_evening")],
        [InlineKeyboardButton("◀ Назад", callback_data="admin_menu")],
    ])


def sources_list_keyboard(sources: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for s in sources:
        icon = "✅" if s["active"] else "❌"
        type_icon = "📡" if s["source_type"] == "telegram" else "🌐"
        label = f"{icon} {type_icon} {s['name']}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"src_info_{s['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"src_del_{s['id']}"),
            InlineKeyboardButton("🔄", callback_data=f"src_toggle_{s['id']}"),
        ])
    rows.append([InlineKeyboardButton("◀ Назад", callback_data="admin_sources")])
    return InlineKeyboardMarkup(rows)


# ── Handlers ────────────────────────────────────────────────────────────────

@_owner_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[STATE] = S_IDLE
    await update.message.reply_text(
        "🤖 *Панель управления ботом*\nВыбери раздел:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


@_owner_only
async def admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles free-text replies in admin flows."""
    state = context.user_data.get(STATE)
    text = update.message.text.strip()

    if state == S_WAIT_URL:
        context.user_data[PENDING_URL] = text
        context.user_data[STATE] = S_WAIT_NAME
        src_type = context.user_data.get(PENDING_TYPE, "rss")
        hint = "канала (например «Технологии»)" if src_type == "telegram" else "источника (например «Хабр»)"
        await update.message.reply_text(
            f"Введи название {hint}:\n_(или /skip для автоматического)_",
            parse_mode="Markdown",
        )

    elif state == S_WAIT_NAME:
        url = context.user_data.pop(PENDING_URL, "")
        src_type = context.user_data.pop(PENDING_TYPE, "rss")
        name = text if text.lower() != "/skip" else url

        if not url:
            await update.message.reply_text("⚠️ URL не сохранился, попробуй снова.")
            context.user_data[STATE] = S_IDLE
            return

        add_source(name=name, url=url, source_type=src_type)
        context.user_data[STATE] = S_IDLE
        type_label = "Telegram-канал" if src_type == "telegram" else "RSS/Сайт"
        await update.message.reply_text(
            f"✅ *{type_label}* добавлен!\n`{url}` → {name}",
            parse_mode="Markdown",
            reply_markup=sources_menu_keyboard(),
        )

    elif state == S_WAIT_MORNING:
        if re.match(r"^\d{1,2}:\d{2}$", text):
            set_setting("morning_time", text)
            context.user_data[STATE] = S_IDLE
            await update.message.reply_text(
                f"✅ Утренний дайджест будет в *{text}*",
                parse_mode="Markdown",
                reply_markup=schedule_keyboard(),
            )
            # Reschedule
            _reschedule(context)
        else:
            await update.message.reply_text("Неверный формат. Введи время в формате ЧЧ:ММ, например `08:30`", parse_mode="Markdown")

    elif state == S_WAIT_EVENING:
        if re.match(r"^\d{1,2}:\d{2}$", text):
            set_setting("evening_time", text)
            context.user_data[STATE] = S_IDLE
            await update.message.reply_text(
                f"✅ Вечерний дайджест будет в *{text}*",
                parse_mode="Markdown",
                reply_markup=schedule_keyboard(),
            )
            _reschedule(context)
        else:
            await update.message.reply_text("Неверный формат. Введи время в формате ЧЧ:ММ, например `20:00`", parse_mode="Markdown")


def _reschedule(context: ContextTypes.DEFAULT_TYPE):
    try:
        from scheduler import reschedule_jobs
        reschedule_jobs(context.application)
    except Exception as e:
        logger.warning(f"Reschedule failed: {e}")


@_owner_only
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_menu":
        context.user_data[STATE] = S_IDLE
        await query.edit_message_text(
            "🤖 *Панель управления ботом*\nВыбери раздел:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    elif data == "admin_sources":
        await query.edit_message_text(
            "📰 *Источники новостей*\nДобавляй RSS-ленты или Telegram-каналы:",
            parse_mode="Markdown",
            reply_markup=sources_menu_keyboard(),
        )

    elif data == "admin_schedule":
        await query.edit_message_text(
            "⏰ *Расписание дайджестов*\nВыбери что изменить:",
            parse_mode="Markdown",
            reply_markup=schedule_keyboard(),
        )

    elif data == "admin_add_rss":
        context.user_data[PENDING_TYPE] = "rss"
        context.user_data[STATE] = S_WAIT_URL
        await query.edit_message_text(
            "🌐 *Добавить RSS / Сайт*\n\nВведи URL RSS-ленты:\n"
            "Пример: `https://habr.com/rss/best/`\n\n"
            "Большинство сайтов имеют RSS по адресу `/rss`, `/feed` или `/atom`.",
            parse_mode="Markdown",
        )

    elif data == "admin_add_tg":
        context.user_data[PENDING_TYPE] = "telegram"
        context.user_data[STATE] = S_WAIT_URL
        await query.edit_message_text(
            "📡 *Добавить Telegram-канал*\n\nВведи @username или ссылку на канал:\n"
            "Пример: `@durov` или `https://t.me/durov`\n\n"
            "⚠️ Требуется настройка Telethon (setup\\_telethon.py)",
            parse_mode="Markdown",
        )

    elif data == "admin_list_sources":
        sources = get_all_sources()
        if not sources:
            await query.edit_message_text(
                "📋 *Источников нет*\nДобавь первый источник:",
                parse_mode="Markdown",
                reply_markup=sources_menu_keyboard(),
            )
        else:
            count = len(sources)
            await query.edit_message_text(
                f"📋 *Источники новостей* ({count} шт.)\n\n"
                "✅/❌ — активен | 🗑 — удалить | 🔄 — вкл/выкл",
                parse_mode="Markdown",
                reply_markup=sources_list_keyboard(sources),
            )

    elif data.startswith("src_del_"):
        sid = int(data.split("_")[-1])
        src = get_source(sid)
        if src:
            delete_source(sid)
            await query.edit_message_text(
                f"🗑 *{src['name']}* удалён.",
                parse_mode="Markdown",
                reply_markup=sources_menu_keyboard(),
            )

    elif data.startswith("src_toggle_"):
        sid = int(data.split("_")[-1])
        toggle_source(sid)
        sources = get_all_sources()
        await query.edit_message_text(
            "📋 *Источники новостей*\n\n✅/❌ — активен | 🗑 — удалить | 🔄 — вкл/выкл",
            parse_mode="Markdown",
            reply_markup=sources_list_keyboard(sources),
        )

    elif data.startswith("src_info_"):
        sid = int(data.split("_")[-1])
        src = get_source(sid)
        if src:
            status = "✅ Активен" if src["active"] else "❌ Отключён"
            cat = src.get("category") or "авто"
            await query.answer(
                f"{src['name']}\n{src['url']}\nТип: {src['source_type']}\nКатегория: {cat}\n{status}",
                show_alert=True,
            )

    elif data == "admin_set_morning":
        context.user_data[STATE] = S_WAIT_MORNING
        await query.edit_message_text(
            "🌅 Введи время утреннего дайджеста в формате ЧЧ:ММ\nПример: `08:00`",
            parse_mode="Markdown",
        )

    elif data == "admin_set_evening":
        context.user_data[STATE] = S_WAIT_EVENING
        await query.edit_message_text(
            "🌆 Введи время вечернего дайджеста в формате ЧЧ:ММ\nПример: `20:00`",
            parse_mode="Markdown",
        )

    elif data == "admin_test_morning":
        await query.edit_message_text("⏳ Собираю утренний дайджест...")
        await _send_test_digest(query, context, "morning")

    elif data == "admin_test_evening":
        await query.edit_message_text("⏳ Собираю вечерний дайджест...")
        await _send_test_digest(query, context, "evening")


async def _send_test_digest(query, context, digest_type: str):
    from digest import build_morning_digest, build_evening_digest, split_message

    try:
        if digest_type == "morning":
            text = await build_morning_digest()
        else:
            text = await build_evening_digest()

        chunks = split_message(text)
        for chunk in chunks:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=chunk,
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.exception("Test digest error")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"❌ Ошибка при сборке дайджеста:\n`{e}`",
            parse_mode="Markdown",
        )
