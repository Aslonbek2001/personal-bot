import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from bot.content import loader
from bot.handlers import build_router, scheduled
from bot.handlers.fsm import SQLiteStorage
from bot.services import db


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    library = loader.current()
    db.init()
    storage = SQLiteStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(build_router())

    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(
        scheduled.morning_lesson,
        CronTrigger(hour=settings.lesson_hour, minute=0, timezone=settings.tz),
        kwargs={"bot": bot, "chat_id": settings.owner_id},
        id="morning_lesson",
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.add_job(
        scheduled.evening_summary,
        CronTrigger(hour=settings.reminder_hour, minute=0, timezone=settings.tz),
        kwargs={"bot": bot, "chat_id": settings.owner_id},
        id="evening_summary",
        misfire_grace_time=3600,
        coalesce=True,
    )
    owner_state = FSMContext(
        storage=storage,
        key=StorageKey(bot_id=bot.id, chat_id=settings.owner_id, user_id=settings.owner_id),
    )
    scheduler.add_job(
        scheduled.weekly_review,
        CronTrigger(day_of_week=settings.review_day, hour=settings.review_hour, minute=0, timezone=settings.tz),
        kwargs={"bot": bot, "chat_id": settings.owner_id, "state": owner_state},
        id="weekly_review",
        misfire_grace_time=3600,
        coalesce=True,
    )

    try:
        me = await bot.get_me()
        scheduler.start()
        logging.info(
            "Ustoz ishga tushdi: @%s, %d ta fan, dars %02d:00, natija %02d:00, takrorlash %s %02d:00",
            me.username, len(library.subjects), settings.lesson_hour, settings.reminder_hour,
            settings.review_day, settings.review_hour,
        )
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
