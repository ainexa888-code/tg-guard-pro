import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import (
    add_keyword_reaction,
    get_group_settings,
    get_keyword_reactions,
    remove_keyword_reaction,
    update_group_settings,
)
from app.services.analytics import AnalyticsService
from app.services.reactions import ReactionEngine

logger = logging.getLogger("tg_guard_pro.handlers.reactions")
router = Router(name="reactions")


@router.message(Command("reaction"))
async def cmd_reaction(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Manages keyword auto-reactions: on, off, add, remove, list, test."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही रिएक्शन सेटिंग्स बदल सकते हैं।")
        return

    text = message.text or ""
    parts = text.split(maxsplit=3)
    if len(parts) < 2:
        await message.reply(
            "⚡ <b>ऑटो-रिएक्शन कमांड्स:</b>\n\n"
            "• <code>/reaction on</code> — रिएक्शन्स चालू करें\n"
            "• <code>/reaction off</code> — रिएक्शन्स बंद करें\n"
            "• <code>/reaction add &lt;keyword&gt; &lt;emoji&gt;</code> — कीवर्ड जोड़ें\n"
            "• <code>/reaction remove &lt;keyword&gt;</code> — कीवर्ड हटाएं\n"
            "• <code>/reaction list</code> — सभी कीवर्ड्स देखें\n"
            "• <code>/reaction test &lt;keyword&gt;</code> — टेस्ट करें"
        )
        return

    action = parts[1].lower()

    if action == "on":
        await update_group_settings(session, message.chat.id, auto_reactions=True)
        await message.reply("✅ कीवर्ड ऑटो-रिएक्शन चालू (Enabled) कर दिया गया है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, auto_reactions=False)
        await message.reply("🛑 कीवर्ड ऑटो-रिएक्शन बंद (Disabled) कर दिया गया है।")
    elif action == "add":
        if len(parts) < 4:
            await message.reply(
                "⚠️ कृपया कीवर्ड और इमोजी दोनों दें: <code>/reaction add hello ❤️</code>"
            )
            return
        kw = parts[2]
        emoji = parts[3].strip()
        await add_keyword_reaction(session, message.chat.id, kw, emoji)
        await message.reply(
            f"✅ कीवर्ड <code>{kw}</code> के लिए इमोजी <b>{emoji}</b> सेट हो गया है।"
        )
    elif action == "remove":
        if len(parts) < 3:
            await message.reply(
                "⚠️ कृपया हटाने के लिए कीवर्ड दें: <code>/reaction remove hello</code>"
            )
            return
        kw = parts[2]
        removed = await remove_keyword_reaction(session, message.chat.id, kw)
        if removed:
            await message.reply(f"🗑️ कीवर्ड <code>{kw}</code> हटा दिया गया।")
        else:
            await message.reply(f"⚠️ कीवर्ड <code>{kw}</code> नहीं मिला।")
    elif action == "list":
        reactions = await get_keyword_reactions(session, message.chat.id)
        if not reactions:
            await message.reply("ℹ️ इस ग्रुप में अभी कोई ऑटो-रिएक्शन कीवर्ड कॉन्फ़िगर नहीं है।")
            return
        lines = [f"• <code>{kw}</code> ➔ {em}" for kw, em in reactions.items()]
        await message.reply("⚡ <b>सक्रिय ऑटो-रिएक्शन कीवर्ड्स:</b>\n\n" + "\n".join(lines))
    elif action == "test":
        if len(parts) < 3:
            await message.reply(
                "⚠️ टेस्ट करने के लिए शब्द दें: <code>/reaction test hello</code>"
            )
            return
        test_kw = parts[2]
        reactions = await get_keyword_reactions(session, message.chat.id)
        emoji = ReactionEngine.match_keyword(test_kw, reactions)
        if emoji:
            await message.reply(
                f"🎯 टेस्ट सफल! शब्द '<code>{test_kw}</code>' इमोजी <b>{emoji}</b> को ट्रिगर करेगा।"
            )
        else:
            await message.reply(
                f"❌ शब्द '<code>{test_kw}</code>' से कोई रिएक्शन मैच नहीं हुआ।"
            )


async def handle_message_reaction(
    message: Message, bot: Bot, session: AsyncSession
) -> None:
    """Triggered on normal group messages to evaluate keyword reactions."""
    if not message.text or message.text.startswith("/"):
        return

    settings = await get_group_settings(session, message.chat.id)
    if not settings or not settings.auto_reactions:
        return

    reactions = await get_keyword_reactions(session, message.chat.id)
    if not reactions:
        return

    success = await ReactionEngine.try_react(
        bot=bot,
        chat_id=message.chat.id,
        message_id=message.message_id,
        user_id=message.from_user.id,
        text=message.text,
        keyword_map=reactions,
        cooldown_seconds=settings.reaction_cooldown,
    )
    if success:
        await AnalyticsService.record_event(message.chat.id, "reactions_count", 1)
