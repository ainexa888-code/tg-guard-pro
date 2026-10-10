import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import get_group_settings
from app.services.analytics import AnalyticsService

logger = logging.getLogger("tg_guard_pro.handlers.analytics")
router = Router(name="analytics")


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Displays group analytics for 1d, 7d, or 30d."""
    if message.chat.type == "private":
        await message.reply("यह कमांड केवल ग्रुप में कार्य करता है।")
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ग्रुप के आंकड़े देख सकते हैं।")
        return

    days = 7
    parts = message.text.split() if message.text else []
    if len(parts) > 1:
        arg = parts[1].lower().replace("d", "")
        if arg.isdigit() and int(arg) in (1, 7, 30, 90):
            days = int(arg)

    settings = await get_group_settings(session, message.chat.id)
    lang = settings.language if settings else "hi"

    report = await AnalyticsService.format_analytics_report(
        message.chat.id, days=days, language=lang
    )
    await message.reply(report)
