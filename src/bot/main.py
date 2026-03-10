import asyncio

from bot.app import create_bot_and_dispatcher
from core.config import settings
from core.logging import setup_logging
from db.seed import seed_system_catalog
from db.session import SessionLocal


async def run() -> None:
    setup_logging(settings.log_level)

    async with SessionLocal() as session:
        await seed_system_catalog(session)

    bot, dp = create_bot_and_dispatcher()

    # Ensure polling is not blocked by stale webhook configuration.
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
