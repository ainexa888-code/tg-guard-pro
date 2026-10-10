import logging

from aiogram import Bot, Router
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import (
    get_group_settings,
    update_group_settings,
)
from app.services.antiraid import AntiRaidService
from app.services.audit import AuditService

logger = logging.getLogger("tg_guard_pro.handlers.antiraid")
router = Router(name="antiraid")


@router.message(Command("antiraid"))
async def cmd_antiraid(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Toggles anti-raid system."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही एंटी-रेड सेटिंग्स बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "🚨 <b>एंटी-रेड कमांड्स:</b>\n\n"
            "• <code>/antiraid on</code> — एंटी-रेड सुरक्षा चालू करें\n"
            "• <code>/antiraid off</code> — एंटी-रेड सुरक्षा बंद करें\n"
            "• <code>/raidlimit 20</code> — 60 सेकंड में जॉइन सीमा सेट करें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, anti_raid=True)
        await message.reply("✅ एंटी-रेड सुरक्षा चालू (ON) कर दी गई है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, anti_raid=False)
        await message.reply("🛑 एंटी-रेड सुरक्षा बंद (OFF) कर दी गई है।")


@router.message(Command("raidlimit"))
async def cmd_raidlimit(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Sets join rate threshold."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
        if 5 <= limit <= 100:
            await update_group_settings(session, message.chat.id, raid_limit=limit)
            await message.reply(
                f"✅ एंटी-रेड सीमा <b>{limit} सदस्य / 60 सेकंड</b> पर सेट की गई।"
            )
            return

    await message.reply("⚠️ कृपया 5 से 100 के बीच की संख्या दें: <code>/raidlimit 20</code>")


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def monitor_join_for_raid(
    event: ChatMemberUpdated, bot: Bot, session: AsyncSession
) -> None:
    """Monitors joining rate to detect massive bot raids."""
    if event.chat.type == "private":
        return

    settings = await get_group_settings(session, event.chat.id)
    if not settings or not settings.anti_raid:
        return

    is_raid, count = AntiRaidService.record_join_and_check_raid(
        chat_id=event.chat.id,
        raid_limit=settings.raid_limit,
        raid_window=settings.raid_window,
    )

    if is_raid:
        alert_msg = (
            f"🚨 <b>एंटी-रेड अलर्ट (ANTI-RAID TRIGGERED)!</b>\n\n"
            f"ग्रुप में अप्रत्याशित रूप से <b>{count}</b> सदस्य 60 सेकंड के भीतर शामिल हुए हैं!\n"
            f"सिस्टम ने स्वचालित रूप से सुरक्षा स्तर बढ़ा दिया है।"
        )
        try:
            await bot.send_message(chat_id=event.chat.id, text=alert_msg)
            await AuditService.log_action(
                bot=bot,
                chat_id=event.chat.id,
                action="raid_detected",
                details={"burst_count": count},
                is_security_alert=True,
            )
        except Exception as e:
            logger.error(f"Error notifying anti-raid: {e}")
