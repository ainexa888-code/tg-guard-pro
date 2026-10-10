from collections.abc import Collection

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message


class ChatTypeFilter(Filter):
    def __init__(self, chat_types: str | Collection[str]):
        if isinstance(chat_types, str):
            self.chat_types = [chat_types]
        else:
            self.chat_types = list(chat_types)

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        chat = event.chat if isinstance(event, Message) else event.message.chat
        return chat.type in self.chat_types
