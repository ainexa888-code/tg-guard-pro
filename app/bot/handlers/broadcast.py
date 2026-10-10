import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import IsBotOwnerFilter
from app.config import get_settings
from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import update_group_settings
from app.services.broadcast import BroadcastService

settings = get_settings()
logger = logging.getLogger("tg_guard_pro.handlers.broadcast")
router = Router(name="broadcast")


@router.message(Command("broadcast"), IsBotOwnerFilter())
async def cmd_broadcast(message: Message, bot: Bot) -> None:
    """Owner command to broadcast an announcement across all opted-in groups."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "⚠️ कृपया प्रसारण संदेश लिखें: <code>/broadcast &lt;message&gt;</code>"
        )
        return

    broadcast_text = parts[1]
    status_msg = await message.reply("🚀 ब्रॉडकास्ट शुरू किया जा रहा है...")

    results = await BroadcastService.run_broadcast(
        bot=bot,
        creator_id=message.from_user.id,
        message_text=broadcast_text,
    )

    await status_msg.edit_text(
        f"📢 <b>ब्रॉडकास्ट पूरा हुआ!</b>\n\n"
        f"• कैंपेन ID: <code>{results['campaign_id']}</code>\n"
        f"• कुल लक्षित ग्रुप: <b>{results['total']}</b>\n"
        f"• सफलतापूर्वक भेजे गए: <b>{results['success']}</b>\n"
        f"• विफल: <b>{results['failed']}</b>"
    )


@router.message(Command("broadcastoptin"))
async def cmd_broadcast_optin(
    message: Message, bot: Bot, session: AsyncSession
) -> None:
    """Group admin opts into receiving global announcements."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    await update_group_settings(session, message.chat.id, broadcast_optin=True)
    await message.reply(
        "✅ इस ग्रुप को बॉट घोषणाओं और अपडेट्स (Broadcast) के लिए सक्षम (Opted-in) कर दिया गया है।"
    )


@router.message(Command("broadcastoptout"))
async def cmd_broadcast_optout(
    message: Message, bot: Bot, session: AsyncSession
) -> None:
    """Group admin opts out of receiving global announcements."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    await update_group_settings(session, message.chat.id, broadcast_optin=False)
    await message.reply(
        "🛑 इस ग्रुप को बॉट घोषणाओं से बाहर (Opted-out) कर दिया गया है। अब कोई मास ब्रॉडकास्ट नहीं आएगा।"
    )
