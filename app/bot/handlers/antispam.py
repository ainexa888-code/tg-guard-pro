import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import (
    get_group_settings,
    update_group_settings,
)
from app.services.analytics import AnalyticsService
from app.services.antispam import AntiSpamService
from app.services.moderation import ModerationService

logger = logging.getLogger("tg_guard_pro.handlers.antispam")
router = Router(name="antispam")


@router.message(Command("antispam"))
async def cmd_antispam(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Enables or disables anti-spam."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही एंटी-स्पैम सेटिंग्स बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "🛡️ <b>एंटी-स्पैम कमांड्स:</b>\n\n"
            "• <code>/antispam on</code> — एंटी-स्पैम चालू करें\n"
            "• <code>/antispam off</code> — एंटी-स्पैम बंद करें\n"
            "• <code>/spamlimit 5</code> — मैसेज फ्लड लिमिट सेट करें\n"
            "• <code>/warnlimit 3</code> — अधिकतम चेतावनी सीमा सेट करें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, anti_spam=True)
        await message.reply("✅ एंटी-स्पैम सुरक्षा चालू (ON) कर दी गई है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, anti_spam=False)
        await message.reply("🛑 एंटी-स्पैम सुरक्षा बंद (OFF) कर दी गई है।")


@router.message(Command("spamlimit"))
async def cmd_spamlimit(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Sets messages per 5s limit."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
        if 2 <= limit <= 30:
            await update_group_settings(session, message.chat.id, spam_limit=limit)
            await message.reply(
                f"✅ स्पैम फ्लड सीमा <b>{limit} मैसेज / 5 सेकंड</b> पर सेट की गई।"
            )
            return

    await message.reply("⚠️ कृपया 2 से 30 के बीच की संख्या दें: <code>/spamlimit 5</code>")


@router.message(Command("warnlimit"))
async def cmd_warnlimit(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Sets warning escalation threshold."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
        if 1 <= limit <= 10:
            await update_group_settings(session, message.chat.id, warn_limit=limit)
            await message.reply(f"✅ अधिकतम चेतावनी सीमा <b>{limit}</b> पर सेट की गई।")
            return

    await message.reply("⚠️ कृपया 1 से 10 के बीच की संख्या दें: <code>/warnlimit 3</code>")


async def inspect_spam_message(
    message: Message, bot: Bot, session: AsyncSession
) -> bool:
    """
    Evaluates whether message violates anti-spam rules.
    Returns True if handled.
    """
    if not message.from_user or message.from_user.is_bot:
        return False

    if await is_user_admin(bot, message.chat.id, message.from_user.id):
        return False

    settings = await get_group_settings(session, message.chat.id)
    if not settings or not settings.anti_spam:
        return False

    is_spam, reason = await AntiSpamService.inspect_message(
        message=message,
        spam_limit=settings.spam_limit,
        spam_interval=settings.spam_interval,
    )

    if not is_spam:
        return False

    await AnalyticsService.record_event(message.chat.id, "spam_blocked_count", 1)
    await ModerationService.delete_message_safely(
        bot, message.chat.id, message.message_id
    )

    # Issue warning or mute
    await ModerationService.warn_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        reason=f"Spam detected: {reason}",
        settings=settings,
    )

    return True
