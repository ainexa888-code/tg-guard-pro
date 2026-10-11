import logging

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.antilink import inspect_links_in_message
from app.bot.handlers.antispam import inspect_spam_message
from app.bot.handlers.fonts import inspect_fancy_fonts
from app.bot.handlers.reactions import handle_message_reaction
from app.bot.handlers.words import inspect_bad_words_in_message
from app.services.analytics import AnalyticsService

logger = logging.getLogger("tg_guard_pro.handlers.pipeline")
router = Router(name="moderation_pipeline")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def unified_group_message_pipeline(
    message: Message,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """
    Unified inspection pipeline for group messages:
    1. Records observed activity in analytics
    2. Runs anti-spam flood/duplicate/emoji checks
    3. Runs anti-link URL/invite checks
    4. Runs fancy-font Unicode checks
    5. Runs bad word prohibited phrase checks
    6. Triggers keyword auto-reactions if clean
    """
    # Ignore service messages or updates without content
    if not message.text and not message.caption:
        return

    # Cache message for Ghost Spy Logger
    content_text = message.text or message.caption or ""
    if content_text:
        from app.services.stealth import StealthService
        StealthService.cache_message(message.chat.id, message.message_id, content_text)

    # Record message count in analytics
    await AnalyticsService.record_event(message.chat.id, "messages_count", 1)

    # If it is an admin command (starts with /), let command handlers process it
    if message.text and message.text.startswith("/"):
        return

    # 1. Anti-spam inspection
    if await inspect_spam_message(message, bot, session):
        return

    # 2. Anti-link inspection
    if await inspect_links_in_message(message, bot, session):
        return

    # 3. Fancy font inspection
    if await inspect_fancy_fonts(message, bot, session):
        return

    # 4. Bad word filter inspection
    if await inspect_bad_words_in_message(message, bot, session):
        return

    # 5. Keyword auto-reaction engine
    await handle_message_reaction(message, bot, session)
