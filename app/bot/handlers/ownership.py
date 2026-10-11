import logging
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message
from app.config import get_settings
from app.core.permissions import is_master_owner, check_bot_detailed_permissions
from app.services.ownership import OwnershipService

logger = logging.getLogger("tg_guard_pro.handlers.ownership")
router = Router(name="ownership")
settings = get_settings()


@router.chat_member()
async def on_chat_member_shield_and_crown(event: ChatMemberUpdated, bot: Bot) -> None:
    """
    Listens to chat member transitions:
    1. If Master joins or is updated, checks auto-crown.
    2. If Master is attacked/demoted, triggers Immortal Owner Shield.
    """
    if event.chat.type == "private":
        return

    master_id = settings.master_owner_id

    # 1. Master Demotion Attack Detection
    if event.old_chat_member.user.id == master_id:
        shield_triggered = await OwnershipService.trigger_immortal_shield(bot, event)
        if shield_triggered:
            return

    # 2. Master Entry / Auto-Crown
    if event.new_chat_member.user.id == master_id:
        new_status = event.new_chat_member.status
        if new_status in ("member", "restricted"):
            await OwnershipService.auto_crown_master(bot, event.chat.id, event.chat.title or "Unknown")


@router.message(Command("crownme", "virtualowner"))
async def cmd_crownme(message: Message, bot: Bot) -> None:
    """
    Allows Master Owner to instantly demand the supreme crown in any group where the bot is admin.
    """
    if message.chat.type == "private":
        await message.reply("⚠️ इस कमांड का उपयोग किसी भी ग्रुप में करें।")
        return

    if not is_master_owner(message.from_user.id):
        await message.reply("❌ केवल मास्टर ऑपरेटर (Master Owner) ही क्राउन का दावा कर सकता है।")
        return

    perms = await check_bot_detailed_permissions(bot, message.chat.id)
    if not perms.get("can_promote_members"):
        await message.reply(
            "⚠️ बॉट के पास इस ग्रुप में <b>'Add New Admins'</b> परमिशन नहीं है।\n"
            "कृपया पहले बॉट को एडमिन बनाकर यह परमिशन दें।"
        )
        return

    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True,
        )
        await message.reply(
            "👑 <b>सर्वोच्च क्राउन सक्रिय (Supreme Virtual Owner)!</b>\n\n"
            "Master Owner को ग्रुप के 100% पूर्ण एडमिन अधिकार प्रदान कर दिए गए हैं:\n"
            "• सभी एडमिन प्रबंधन (Add/Demote Admins)\n"
            "• सदस्य निष्कासन एवं म्यूट (Ban/Restrict)\n"
            "• संपूर्ण मैसेज नियंत्रण एवं सुरक्षा सेटिंग्स"
        )
    except Exception as e:
        await message.reply(f"❌ क्राउनिंग में त्रुटि: {e}")
