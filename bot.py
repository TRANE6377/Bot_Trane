"""Main entry point for the digest bot."""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, OWNER_ID
from database import init_db
from admin_panel import (
    admin_command,
    admin_callback,
    admin_text_input,
    STATE, S_IDLE,
)
from scheduler import setup_scheduler, start_scheduler

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    await update.message.reply_text(
        "👋 *Привет! Я твой персональный дайджест-бот.*\n\n"
        "Каждое утро и вечер буду присылать тебе сводку.\n\n"
        "📋 Команды:\n"
        "• /admin — панель управления\n"
        "• /digest — получить утренний дайджест сейчас\n"
        "• /evening — получить вечерний дайджест сейчас\n"
        "• /help — справка",
        parse_mode="Markdown",
    )


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    from digest import build_morning_digest, split_message
    msg = await update.message.reply_text("⏳ Собираю утренний дайджест...")
    try:
        text = await build_morning_digest()
        await msg.delete()
        for chunk in split_message(text):
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Digest command error")
        await msg.edit_text(f"❌ Ошибка: `{e}`", parse_mode="Markdown")


async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    from digest import build_evening_digest, split_message
    msg = await update.message.reply_text("⏳ Собираю вечерний дайджест...")
    try:
        text = await build_evening_digest()
        await msg.delete()
        for chunk in split_message(text):
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Evening digest command error")
        await msg.edit_text(f"❌ Ошибка: `{e}`", parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text(
        "📖 *Справка*\n\n"
        "/start — приветствие\n"
        "/admin — панель управления (источники, расписание)\n"
        "/digest — утренний дайджест прямо сейчас\n"
        "/evening — вечерний дайджест прямо сейчас\n"
        "/help — эта справка\n\n"
        "В /admin ты можешь:\n"
        "• Добавить RSS-ленты и Telegram-каналы\n"
        "• Изменить время утреннего и вечернего дайджеста\n"
        "• Протестировать дайджест",
        parse_mode="Markdown",
    )


def _is_admin_state(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return context.user_data.get(STATE) not in (S_IDLE, None)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if _is_admin_state(context):
        await admin_text_input(update, context)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")
    if not OWNER_ID:
        raise RuntimeError("OWNER_ID не задан в .env")

    init_db()
    logger.info(f"DB initialized. Owner: {OWNER_ID}")

    app = Application.builder().token(BOT_TOKEN).post_init(start_scheduler).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("evening", cmd_evening))

    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    setup_scheduler(app)

    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
