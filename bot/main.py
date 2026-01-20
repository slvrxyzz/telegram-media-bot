import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import get_settings
from bot.db.models import Base
from bot.db.session import get_engine, get_session_factory, set_session_factory
from bot.handlers import common, query, upload


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_session_factory(get_session_factory(engine))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    await init_db()

    bot = Bot(token=settings.bot_token, parse_mode="HTML")
    dispatcher = Dispatcher()
    dispatcher.include_router(common.router)
    dispatcher.include_router(upload.router)
    dispatcher.include_router(query.router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

