import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import edit_flow, exercise_flow, main_menu, start, workout_flow
from bot.middlewares.event_logger import EventLoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from core.config import settings
from core.logging import setup_logging
from db.seed import seed_system_catalog
from db.session import SessionLocal


async def run() -> None:
    setup_logging(settings.log_level)

    async with SessionLocal() as session:
        await seed_system_catalog(session)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(EventLoggingMiddleware())
    dp.callback_query.middleware(EventLoggingMiddleware())
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    dp.include_router(start.router)
    dp.include_router(main_menu.router)
    dp.include_router(workout_flow.router)
    dp.include_router(exercise_flow.router)
    dp.include_router(edit_flow.router)

    # Ensure polling is not blocked by stale webhook configuration.
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
