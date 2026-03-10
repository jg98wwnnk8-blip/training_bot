from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import edit_flow, exercise_flow, main_menu, start, workout_flow
from bot.middlewares.event_logger import EventLoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from core.config import settings


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
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

    return bot, dp
