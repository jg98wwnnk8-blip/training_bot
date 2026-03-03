from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, period_seconds: float = 0.35) -> None:
        self.period_seconds = period_seconds
        self._last_seen: dict[tuple[int, str], float] = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = 0
        event_type = "other"
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            event_type = "message"
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            event_type = "callback"

        if user_id:
            key = (user_id, event_type)
            now = time.monotonic()
            last = self._last_seen[key]
            if now - last < self.period_seconds:
                if isinstance(event, CallbackQuery):
                    await event.answer("Слишком быстро, подождите секунду")
                return None
            self._last_seen[key] = now

        return await handler(event, data)
