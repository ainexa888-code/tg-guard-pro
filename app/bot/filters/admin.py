from aiogram import Bot
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.core.permissions import is_user_admin

settings = get_settings()


class IsGroupAdminFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery, bot: Bot) -> bool:
        user = event.from_user
        if not user:
            return False

        chat = event.chat if isinstance(event, Message) else event.message.chat
        if chat.type == "private":
            return (
                True  # In private chats, users can manage their own settings/dashboard
            )

        # Group chats: Check Telegram chat administrator rights
        return await is_user_admin(bot, chat.id, user.id)


class IsBotOwnerFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if not user:
            return False
        return user.id == settings.owner_id
