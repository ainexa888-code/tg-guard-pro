from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.security import is_rate_limited


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, cooldown: float = 0.5):
        self.cooldown = cooldown

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if (
            isinstance(event, Message)
            and event.from_user
            or isinstance(event, CallbackQuery)
            and event.from_user
        ):
            user_id = event.from_user.id

        if user_id:
            if is_rate_limited(
                user_id, "global_throttle", cooldown_seconds=self.cooldown
            ):
                # Drop request or answer callback query quietly
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⚠️ Please slow down.", show_alert=False)
                    except Exception:
                        pass
                return None

        return await handler(event, data)
