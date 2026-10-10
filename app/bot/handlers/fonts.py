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
from app.services.fonts import detect_fancy_fonts
from app.services.moderation import ModerationService

logger = logging.getLogger("tg_guard_pro.handlers.fonts")
router = Router(name="fonts")


@router.message(Command("font"))
async def cmd_font(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Manages fancy font moderation engine."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही फॉन्ट सेटिंग्स बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "🔤 <b>फैंसी फॉन्ट डिटेक्शन कमांड्स:</b>\n\n"
            "• <code>/font on</code> — फॉन्ट डिटेक्शन चालू करें\n"
            "• <code>/font off</code> — फॉन्ट डिटेक्शन बंद करें\n"
            "• <code>/font mode warn</code> — चेतावनी मोड सेट करें\n"
            "• <code>/font mode delete</code> — मैसेज डिलीट मोड सेट करें"
        )
        return

    action = parts[1].lower()

    if action == "on":
        await update_group_settings(session, message.chat.id, fancy_font_detection=True)
        await message.reply("✅ फैंसी फॉन्ट डिटेक्शन चालू (ON) कर दिया गया है।")
    elif action == "off":
        await update_group_settings(
            session, message.chat.id, fancy_font_detection=False
        )
        await message.reply("🛑 फैंसी फॉन्ट डिटेक्शन बंद (OFF) कर दिया गया है।")
    elif action == "mode" and len(parts) > 2:
        mode = parts[2].lower()
        if mode in ("warn", "delete"):
            await update_group_settings(
                session, message.chat.id, fancy_font_action=mode
            )
            await message.reply(
                f"✅ फैंसी फॉन्ट एक्शन मोड <b>{mode.upper()}</b> पर सेट कर दिया गया है।"
            )
        else:
            await message.reply(
                "⚠️ अमान्य मोड। केवल <code>warn</code> या <code>delete</code> चुनें।"
            )


async def inspect_fancy_fonts(
    message: Message, bot: Bot, session: AsyncSession
) -> bool:
    """
    Checks if a message contains unauthorized stylized fonts.
    Returns True if violated and handled (caller should stop processing message).
    """
    text = message.text or message.caption or ""
    if not text or message.from_user.is_bot:
        return False

    # Admins are exempt
    if await is_user_admin(bot, message.chat.id, message.from_user.id):
        return False

    settings = await get_group_settings(session, message.chat.id)
    if not settings or not settings.fancy_font_detection:
        return False

    is_fancy, count = detect_fancy_fonts(text)
    if not is_fancy:
        return False

    await AnalyticsService.record_event(message.chat.id, "fonts_blocked_count", 1)

    if settings.fancy_font_action == "delete":
        await ModerationService.delete_message_safely(
            bot, message.chat.id, message.message_id
        )
        notice = await message.answer(
            f"⚠️ {message.from_user.mention_html()}, इस ग्रुप में फैंसी/स्टाइलिश यूनिकोड फॉन्ट्स की अनुमति नहीं है।"
        )
    else:  # "warn"
        await ModerationService.warn_user(
            bot=bot,
            session=session,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            reason="Fancy font violation",
            settings=settings,
        )
        await ModerationService.delete_message_safely(
            bot, message.chat.id, message.message_id
        )

    return True
