from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import upsert_user


class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")
        user = None

        if (
            isinstance(event, Message)
            and event.from_user
            or isinstance(event, CallbackQuery)
            and event.from_user
        ):
            user = event.from_user

        if user and session:
            try:
                await upsert_user(
                    session=session,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_bot=user.is_bot,
                )
            except Exception:
                pass

        return await handler(event, data)
