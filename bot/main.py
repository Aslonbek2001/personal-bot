import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot import handlers
from bot.config import settings


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(handlers.router)

    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(
        handlers.send_lesson,
        CronTrigger(hour=settings.lesson_hour, minute=0, timezone=settings.tz),
        kwargs={"bot": bot, "chat_id": settings.owner_id, "morning": True},
        id="morning_lesson",
        misfire_grace_time=3600,
        coalesce=True,
    )

    try:
        me = await bot.get_me()
        scheduler.start()
        logging.info("Bot ishga tushdi: @%s, dars har kuni %02d:00 da", me.username, settings.lesson_hour)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())