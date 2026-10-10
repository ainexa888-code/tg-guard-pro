import logging
import re

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.core.security import normalize_unicode
from app.database.repositories.group_repo import (
    add_blocked_word,
    get_blocked_words,
    get_group_settings,
    remove_blocked_word,
    update_group_settings,
)
from app.services.analytics import AnalyticsService
from app.services.moderation import ModerationService

logger = logging.getLogger("tg_guard_pro.handlers.words")
router = Router(name="words")


@router.message(Command("badword"))
async def cmd_badword(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Manages bad word filter."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 2:
        await message.reply(
            "🤬 <b>बैड वर्ड फिल्टर कमांड्स:</b>\n\n"
            "• <code>/badword on</code> — फिल्टर चालू करें\n"
            "• <code>/badword off</code> — फिल्टर बंद करें\n"
            "• <code>/badword add &lt;word&gt;</code> — प्रतिबंधित शब्द जोड़ें\n"
            "• <code>/badword remove &lt;word&gt;</code> — शब्द हटाएं\n"
            "• <code>/badword list</code> — ब्लॉक किए गए शब्द देखें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, bad_word_filter=True)
        await message.reply("✅ बैड वर्ड फिल्टर चालू (ON) कर दिया गया है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, bad_word_filter=False)
        await message.reply("🛑 बैड वर्ड फिल्टर बंद (OFF) कर दिया गया है।")
    elif action == "add":
        if len(parts) < 3:
            await message.reply(
                "⚠️ कृपया जोड़ने के लिए शब्द दें: <code>/badword add badword</code>"
            )
            return
        w = parts[2].strip()
        await add_blocked_word(session, message.chat.id, w)
        await message.reply(
            f"🚫 शब्द '<code>{w}</code>' को प्रतिबंधित सूची में जोड़ दिया गया है।"
        )
    elif action == "remove":
        if len(parts) < 3:
            await message.reply(
                "⚠️ कृपया हटाने के लिए शब्द दें: <code>/badword remove badword</code>"
            )
            return
        w = parts[2].strip()
        removed = await remove_blocked_word(session, message.chat.id, w)
        if removed:
            await message.reply(f"🗑️ शब्द '<code>{w}</code>' को हटा दिया गया।")
        else:
            await message.reply(f"⚠️ शब्द '<code>{w}</code>' सूची में नहीं मिला।")
    elif action == "list":
        words = await get_blocked_words(session, message.chat.id)
        if not words:
            await message.reply("ℹ️ कोई प्रतिबंधित शब्द सूची में नहीं है।")
            return
        await message.reply(
            "🤬 <b>ब्लॉक किए गए शब्द:</b>\n\n"
            + ", ".join(f"<code>{w}</code>" for w in words)
        )


async def inspect_bad_words_in_message(
    message: Message, bot: Bot, session: AsyncSession
) -> bool:
    """
    Scans message for prohibited words.
    Returns True if violation was found and handled.
    """
    text = message.text or message.caption or ""
    if not text or not message.from_user or message.from_user.is_bot:
        return False

    if await is_user_admin(bot, message.chat.id, message.from_user.id):
        return False

    settings = await get_group_settings(session, message.chat.id)
    if not settings or not settings.bad_word_filter:
        return False

    blocked_words = await get_blocked_words(session, message.chat.id)
    if not blocked_words:
        return False

    normalized_text = normalize_unicode(text).lower()

    for word in blocked_words:
        pattern = r"(?<!\w)" + re.escape(word.lower()) + r"(?!\w)"
        if re.search(pattern, normalized_text):
            await AnalyticsService.record_event(
                message.chat.id, "badwords_blocked_count", 1
            )
            await ModerationService.delete_message_safely(
                bot, message.chat.id, message.message_id
            )

            if settings.bad_word_action == "warn":
                await ModerationService.warn_user(
                    bot=bot,
                    session=session,
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    reason=f"Prohibited word detected: {word}",
                    settings=settings,
                )
            return True

    return False
