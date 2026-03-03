from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from core.logging import EventAdapter


class EventLoggingMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.logger = EventAdapter(logging.getLogger("bot.events"), extra={})

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = "-"
        chat_id = "-"
        action = "event"

        if isinstance(event, Message):
            user_id = str(event.from_user.id if event.from_user else "-")
            chat_id = str(event.chat.id)
            action = "message"
        elif isinstance(event, CallbackQuery):
            user_id = str(event.from_user.id)
            chat_id = str(event.message.chat.id if event.message else "-")
            action = f"callback:{event.data}"

        self.logger.info(
            "incoming",
            extra={"action": action, "user_id": user_id, "chat_id": chat_id},
        )
        return await handler(event, data)
