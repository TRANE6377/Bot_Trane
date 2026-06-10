"""APScheduler setup for automatic morning and evening digests."""

import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from config import OWNER_ID
from database import get_setting

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _send_digest(app: Application, digest_type: str):
    from digest import build_morning_digest, build_evening_digest, split_message

    logger.info(f"Sending {digest_type} digest to {OWNER_ID}")
    try:
        if digest_type == "morning":
            text = await build_morning_digest()
        else:
            text = await build_evening_digest()

        for chunk in split_message(text):
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text=chunk,
                parse_mode="Markdown",
            )
    except Exception:
        logger.exception(f"Failed to send {digest_type} digest")


def setup_scheduler(app: Application):
    global _scheduler
    tz_name = get_setting("timezone", "Europe/Moscow")
    tz = pytz.timezone(tz_name)

    _scheduler = AsyncIOScheduler(timezone=tz)

    morning_time = get_setting("morning_time", "08:00")
    evening_time = get_setting("evening_time", "20:00")
    m_h, m_m = morning_time.split(":")
    e_h, e_m = evening_time.split(":")

    _scheduler.add_job(
        _send_digest,
        CronTrigger(hour=int(m_h), minute=int(m_m), timezone=tz),
        id="morning_digest",
        args=[app, "morning"],
        replace_existing=True,
    )
    _scheduler.add_job(
        _send_digest,
        CronTrigger(hour=int(e_h), minute=int(e_m), timezone=tz),
        id="evening_digest",
        args=[app, "evening"],
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(f"Scheduler started — morning: {morning_time}, evening: {evening_time} ({tz_name})")


def reschedule_jobs(app: Application):
    global _scheduler
    if not _scheduler:
        return

    tz_name = get_setting("timezone", "Europe/Moscow")
    tz = pytz.timezone(tz_name)

    morning_time = get_setting("morning_time", "08:00")
    evening_time = get_setting("evening_time", "20:00")
    m_h, m_m = morning_time.split(":")
    e_h, e_m = evening_time.split(":")

    _scheduler.reschedule_job(
        "morning_digest",
        trigger=CronTrigger(hour=int(m_h), minute=int(m_m), timezone=tz),
    )
    _scheduler.reschedule_job(
        "evening_digest",
        trigger=CronTrigger(hour=int(e_h), minute=int(e_m), timezone=tz),
    )
    logger.info(f"Jobs rescheduled — morning: {morning_time}, evening: {evening_time}")
