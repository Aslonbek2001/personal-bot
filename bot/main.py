import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
    try:
        db.init()
    except db.OldSchemaError as error:
        logging.error("%s", error)
        raise SystemExit(1) from None
    library = loader.current()
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = SQLiteStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(build_router())

    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduled.register(scheduler, bot, storage)

    try:
        me = await bot.get_me()
        scheduler.start()
        logging.info(
            "Ustoz ishga tushdi: @%s, %d ta fan, rejali joblar: %s",
            me.username, len(library.subjects), ", ".join(job.id for job in scheduler.get_jobs()),
        )
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
