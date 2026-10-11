import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import ChatMemberOwner, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    can_user_moderate,
    check_bot_detailed_permissions,
    invalidate_admin_cache,
    is_master_owner,
    is_user_admin,
)
from app.database.repositories.group_repo import get_group_settings
from app.database.repositories.moderation_repo import (
    get_audit_logs,
    get_warnings_count,
    reset_warnings,
)
from app.services.moderation import ModerationService

logger = logging.getLogger("tg_guard_pro.handlers.admin")
router = Router(name="admin")


def _get_target_user(message: Message) -> int | None:
    """Helper to extract target user ID from reply or command arguments."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    parts = message.text.split() if message.text else []
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return None


@router.message(Command("admins"))
async def cmd_admins(message: Message, bot: Bot) -> None:
    """Lists current administrators in the group."""
    if message.chat.type == "private":
        await message.reply("यह कमांड केवल ग्रुप में कार्य करता है।")
        return

    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        admin_lines = []
        for a in admins:
            user = a.user
            role = "👑 Owner" if isinstance(a, ChatMemberOwner) else "👮 Admin"
            custom = (
                f" ({a.custom_title})"
                if hasattr(a, "custom_title") and a.custom_title
                else ""
            )
            admin_lines.append(
                f"• {user.full_name} [@{user.username or 'NoUser'}] — {role}{custom}"
            )

        response = "👥 <b>ग्रुप एडमिनिस्ट्रेटर सूची:</b>\n\n" + "\n".join(admin_lines)
        await message.reply(response)
    except Exception as e:
        await message.reply(f"❌ एडमिन सूची प्राप्त करने में त्रुटि: {e}")


@router.message(Command("promote"))
async def cmd_promote(message: Message, bot: Bot) -> None:
    """Promotes a user to group administrator."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास सदस्यों को प्रमोट करने की अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply("⚠️ कृपया प्रमोट करने के लिए यूजर के मैसेज पर रिप्लाई करें: <code>/promote</code>")
        return

    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
        )
        await message.reply(f"👮 यूजर [<code>{target_id}</code>] को ग्रुप एडमिन बना दिया गया है!")
    except Exception as e:
        await message.reply(f"❌ प्रमोट करने में विफलता: {e}\n(कृपया सुनिश्चित करें कि बॉट के पास 'Add New Admins' परमिशन है)")


@router.message(Command("coowner", "superadmin"))
async def cmd_coowner(message: Message, bot: Bot) -> None:
    """Promotes a user to Full Co-Owner / Super Admin with all permissions including adding admins."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास सदस्यों को सुपर एडमिन/को-ओनर बनाने की अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply("⚠️ कृपया को-ओनर बनाने के लिए यूजर के मैसेज पर रिप्लाई करें: <code>/coowner</code> या <code>/superadmin</code>")
        return

    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
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
            f"👑 <b>यूजर [<code>{target_id}</code>] को ग्रुप का 'Super Admin / Co-Owner' बना दिया गया है!</b>\n\n"
            f"✅ <b>पूर्ण अधिकार प्राप्त:</b>\n"
            f"• सभी एडमिन प्रबंधन (Add/Edit Admins)\n"
            f"• सभी सदस्यों को बैन/म्यूट करने की शक्ति\n"
            f"• सभी मैसेज डिलीट और पिन करना\n"
            f"• ग्रुप सेटिंग्स और इनवाइट लिंक्स बदलना"
        )
    except Exception as e:
        await message.reply(
            f"❌ को-ओनर प्रमोट करने में विफलता: {e}\n\n"
            f"💡 <i>नोट: बॉट के पास 'Add New Admins' अधिकार होना अनिवार्य है।</i>"
        )


@router.message(Command("transferowner", "changeowner"))
async def cmd_transferowner(message: Message, bot: Bot) -> None:
    """Explains official Telegram ownership transfer steps and requirements."""
    if message.chat.type == "private":
        await message.reply("⚠️ इस कमांड को ग्रुप में चलाएं।")
        return

    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        owner = next((a for a in admins if a.status == "creator"), None)
        owner_text = f"@{owner.user.username} (ID: <code>{owner.user.id}</code>)" if owner else "अज्ञात"
    except Exception:
        owner_text = "N/A"

    text = (
        f"👑 <b>ग्रुप ओनरशिप ट्रांसफर गाइड ({message.chat.title})</b>\n\n"
        f"• <b>वर्तमान ग्रुप ओनर:</b> {owner_text}\n\n"
        f"⚠️ <b>टेलीग्राम सुरक्षा नियम:</b>\n"
        f"टेलीग्राम बॉट एपीआई सुरक्षा कारणों से किसी बॉट को सीधे ग्रुप का 'Creator Tag' बदलने की अनुमति नहीं देता।\n\n"
        f"📌 <b>ओनरशिप दूसरे व्यक्ति को सौंपने के 2 तरीके हैं:</b>\n\n"
        f"1️⃣ <b>बॉट के जरिए Full Co-Owner (सुपर एडमिन) बनाएं:</b>\n"
        f"• उस यूजर के मैसेज पर रिप्लाई करके <code>/coowner</code> लिखें।\n"
        f"• उसे ओनर जितनी ही सारी पावर्स (किक, बैन, एडमिन बदलना) मिल जाएंगी।\n\n"
        f"2️⃣ <b>असली मालिकाना हक (Official Creator) ट्रांसफर करें:</b>\n"
        f"• वर्तमान ओनर अपने टेलीग्राम ऐप में ग्रुप के नाम पर टैप करें ➔ ✏️ (Edit) दबाएं।\n"
        f"• <b>Administrators</b> में जाएं ➔ नए यूजर को एडमिन बनाएं।\n"
        f"• सबसे नीचे लाल बटन <b>'Transfer Group Ownership'</b> पर टैप करें।\n"
        f"• अपना 2FA पासवर्ड दर्ज करें — ओनरशिप तुरंत ट्रांसफर हो जाएगी!\n\n"
        f"<i>(नोट: ओनरशिप ट्रांसफर के लिए टेलीग्राम खाते पर 2-Step Verification पासवर्ड कम से कम 7 दिन पुराना होना अनिवार्य है)</i>"
    )
    await message.reply(text)


@router.message(Command("shiftadmin", "swapadmin"))
async def cmd_shiftadmin(message: Message, bot: Bot) -> None:
    """
    1-Click Admin Shift: Replaces old admin with new admin.
    Usage:
    - Replying to Old Admin: /shiftadmin <new_user_id>
    - Without reply: /shiftadmin <old_user_id> <new_user_id>
    """
    if message.chat.type == "private":
        await message.reply("⚠️ इस कमांड का उपयोग केवल ग्रुप में करें।")
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास एडमिन अधिकारों को स्थानांतरित करने की अनुमति नहीं है।")
        return

    perms = await check_bot_detailed_permissions(bot, message.chat.id)
    if not perms.get("can_promote_members"):
        await message.reply("❌ बॉट के पास एडमिन प्रमोट/डिमोट करने की 'Add New Admins' परमिशन नहीं है।")
        return

    old_id = None
    new_id = None
    parts = message.text.split() if message.text else []

    if message.reply_to_message and message.reply_to_message.from_user:
        old_id = message.reply_to_message.from_user.id
        if len(parts) > 1 and parts[1].isdigit():
            new_id = int(parts[1])
    elif len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        old_id = int(parts[1])
        new_id = int(parts[2])

    if not old_id or not new_id:
        await message.reply(
            "⚠️ <b>उपयोग विधि:</b>\n"
            "1. पुराने एडमिन के मैसेज पर रिप्लाई करके लिखें:\n"
            "<code>/shiftadmin &lt;new_user_id&gt;</code>\n"
            "2. या दोनों यूजर आईडी दें:\n"
            "<code>/shiftadmin &lt;old_user_id&gt; &lt;new_user_id&gt;</code>"
        )
        return

    if old_id == new_id:
        await message.reply("❌ पुराना और नया एडमिन एक ही यूजर नहीं हो सकते।")
        return

    if new_id == bot.id:
        await message.reply("❌ बॉट को नए एडमिन के रूप में शिफ्ट नहीं किया जा सकता।")
        return

    try:
        old_member = await bot.get_chat_member(message.chat.id, old_id)
        if old_member.status not in ("administrator", "creator"):
            await message.reply(f"⚠️ यूजर [<code>{old_id}</code>] ग्रुप में एडमिन नहीं है।")
            return

        # 1. Promote new admin with all rights
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=new_id,
            can_manage_chat=True,
            can_delete_messages=getattr(old_member, "can_delete_messages", True),
            can_manage_video_chats=getattr(old_member, "can_manage_video_chats", True),
            can_restrict_members=getattr(old_member, "can_restrict_members", True),
            can_promote_members=getattr(old_member, "can_promote_members", True),
            can_change_info=getattr(old_member, "can_change_info", True),
            can_invite_users=getattr(old_member, "can_invite_users", True),
            can_pin_messages=getattr(old_member, "can_pin_messages", True),
            can_manage_topics=getattr(old_member, "can_manage_topics", True),
        )
        invalidate_admin_cache(message.chat.id, new_id)

        # 2. Demote old admin if not creator
        demoted = False
        if old_member.status != "creator":
            await bot.promote_chat_member(
                chat_id=message.chat.id,
                user_id=old_id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
            invalidate_admin_cache(message.chat.id, old_id)
            demoted = True

        demote_note = f"🔴 <b>भूतपूर्व एडमिन [<code>{old_id}</code>]:</b> एडमिन पद से मुक्त" if demoted else f"👑 <b>ग्रुप क्रिएटर [<code>{old_id}</code>]:</b> पद अपरिवर्तनीय"

        await message.reply(
            "🔄 <b>1-क्लिक एडमिन शिफ्टिंग संपन्न (Admin Shift Complete)!</b>\n\n"
            f"{demote_note}\n"
            f"🟢 <b>नया पदधारी एडमिन [<code>{new_id}</code>]:</b> पूर्ण अधिकार प्रदान किए गए\n\n"
            "✨ एडमिन की पूरी जिम्मेदारी सफलतापूर्वक एक यूजर से दूसरे यूजर पर शिफ्ट कर दी गई है।"
        )
    except Exception as e:
        await message.reply(f"❌ एडमिन शिफ्ट करने में त्रुटि: {e}")


@router.message(Command("shiftowner"))
async def cmd_shiftowner(message: Message, bot: Bot) -> None:
    """
    Virtual Ownership Shift: Transfers supreme Co-Owner status to a new user.
    Usage:
    - /shiftowner <new_user_id>
    - Reply to Old Co-Owner with /shiftowner <new_user_id>
    """
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल मास्टर अथवा अधिकृत एडमिन ही ओनरशिप शिफ्ट कर सकते हैं।")
        return

    perms = await check_bot_detailed_permissions(bot, message.chat.id)
    if not perms.get("can_promote_members"):
        await message.reply("❌ बॉट के पास 'Add New Admins' परमिशन नहीं है।")
        return

    parts = message.text.split() if message.text else []
    new_id = None
    old_id = None

    if message.reply_to_message and message.reply_to_message.from_user:
        old_id = message.reply_to_message.from_user.id
        if len(parts) > 1 and parts[1].isdigit():
            new_id = int(parts[1])
    elif len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        old_id = int(parts[1])
        new_id = int(parts[2])
    elif len(parts) == 2 and parts[1].isdigit():
        new_id = int(parts[1])

    if not new_id:
        await message.reply(
            "⚠️ <b>उपयोग विधि:</b>\n"
            "<code>/shiftowner &lt;new_user_id&gt;</code>\n"
            "या पुराने को-ओनर पर रिप्लाई करके:\n"
            "<code>/shiftowner &lt;new_user_id&gt;</code>"
        )
        return

    try:
        # 1. Promote new user with supreme rights
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=new_id,
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
        invalidate_admin_cache(message.chat.id, new_id)

        # 2. Demote old co-owner if specified
        if old_id and old_id != new_id:
            try:
                old_member = await bot.get_chat_member(message.chat.id, old_id)
                if old_member.status != "creator":
                    await bot.promote_chat_member(
                        chat_id=message.chat.id,
                        user_id=old_id,
                        can_manage_chat=False,
                        can_delete_messages=False,
                        can_restrict_members=False,
                        can_promote_members=False,
                        can_change_info=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                    )
                    invalidate_admin_cache(message.chat.id, old_id)
            except Exception:
                pass

        await message.reply(
            "👑 <b>ग्रुप ओनरशिप शिफ्टिंग संपन्न (Ownership Shift Complete)!</b>\n\n"
            f"✨ <b>नया सुप्रीम Co-Owner [<code>{new_id}</code>]:</b>\n"
            "• सभी एडमिन प्रबंधन (Add/Demote Admins)\n"
            "• सभी सदस्यों को बैन/म्यूट करने की शक्ति\n"
            "• सभी ग्रुप सेटिंग्स और पूर्ण नियंत्रण"
        )
    except Exception as e:
        await message.reply(f"❌ ओनरशिप शिफ्ट करने में त्रुटि: {e}")


@router.message(Command("evacuateadmins", "purgeadmins"))
async def cmd_evacuateadmins(message: Message, bot: Bot) -> None:
    """
    Emergency Admin Evacuation: Demotes all non-master admins in 1 shot,
    leaving only Master Owner and Bot in control. Master Owner only.
    """
    from app.config import get_settings
    if message.chat.type == "private":
        return

    if not is_master_owner(message.from_user.id):
        await message.reply("❌ केवल मास्टर ऑपरेटर (Master Owner) ही यह आपातकालीन कमांड चला सकता है।")
        return

    perms = await check_bot_detailed_permissions(bot, message.chat.id)
    if not perms.get("can_promote_members"):
        await message.reply("❌ बॉट के पास 'Add New Admins' परमिशन नहीं है।")
        return

    settings = get_settings()
    master_id = settings.master_owner_id

    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        evacuated = 0
        for a in admins:
            uid = a.user.id
            # Don't demote bot, master, or creator
            if uid == bot.id or uid == master_id or a.status == "creator":
                continue

            try:
                await bot.promote_chat_member(
                    chat_id=message.chat.id,
                    user_id=uid,
                    can_manage_chat=False,
                    can_delete_messages=False,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                )
                invalidate_admin_cache(message.chat.id, uid)
                evacuated += 1
            except Exception:
                pass

        await message.reply(
            f"🚨 <b>आपातकालीन एडमिन निष्कासन संपन्न (Admin Evacuation Complete)!</b>\n\n"
            f"• कुल निष्कासित एडमिन्स: <b>{evacuated}</b>\n"
            f"• ग्रुप का सर्वोच्च नियंत्रण अब केवल <b>Master Owner</b> और <b>बॉट</b> के पास सुरक्षित है।"
        )
    except Exception as e:
        await message.reply(f"❌ एडमिन निष्कासन में त्रुटि: {e}")


@router.message(Command("demote"))
async def cmd_demote(message: Message, bot: Bot) -> None:
    """Demotes an administrator back to regular member."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास सदस्यों को डिमोट करने की अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply("⚠️ कृपया डिमोट करने के लिए यूजर के मैसेज पर रिप्लाई करें: <code>/demote</code>")
        return

    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )
        await message.reply(f"👤 यूजर [<code>{target_id}</code>] के एडमिन अधिकार हटा दिए गए हैं।")
    except Exception as e:
        await message.reply(f"❌ डिमोट करने में विफलता: {e}")


@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Bans a member from the group."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास सदस्यों को बैन करने की अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply(
            "⚠️ कृपया किसी यूजर के मैसेज पर रिप्लाई करें या उसकी User ID दें: <code>/ban &lt;user_id&gt;</code>"
        )
        return

    if await is_user_admin(bot, message.chat.id, target_id):
        await message.reply("❌ किसी एडमिनिस्ट्रेटर को बैन नहीं किया जा सकता।")
        return

    success = await ModerationService.ban_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=target_id,
        reason="Admin command",
        admin_id=message.from_user.id,
    )
    if success:
        await message.reply(
            f"🚫 यूजर [<code>{target_id}</code>] को ग्रुप से बैन कर दिया गया है।"
        )
    else:
        await message.reply(
            "❌ बैन करने में विफलता। कृपया सुनिश्चित करें कि बॉट के पास एडमिन राइट्स हैं।"
        )


@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Unbans a user from the group."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास यह अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply(
            "⚠️ कृपया अनबैन करने के लिए User ID दें: <code>/unban &lt;user_id&gt;</code>"
        )
        return

    success = await ModerationService.unban_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=target_id,
        admin_id=message.from_user.id,
    )
    if success:
        await message.reply(f"✅ यूजर [<code>{target_id}</code>] को अनबैन कर दिया गया है।")
    else:
        await message.reply("❌ अनबैन करने में विफलता।")


@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Mutes a member for a given duration (default 1 hour)."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास सदस्यों को म्यूट करने की अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply(
            "⚠️ कृपया यूजर के मैसेज पर रिप्लाई करें: <code>/mute [minutes]</code>"
        )
        return

    if await is_user_admin(bot, message.chat.id, target_id):
        await message.reply("❌ किसी एडमिन को म्यूट नहीं किया जा सकता।")
        return

    parts = message.text.split() if message.text else []
    duration = 3600  # 1 hour
    if len(parts) > 1 and parts[-1].isdigit():
        duration = int(parts[-1]) * 60

    success = await ModerationService.mute_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=target_id,
        duration_seconds=duration,
        reason="Admin mute",
        admin_id=message.from_user.id,
    )
    if success:
        await message.reply(
            f"🔇 यूजर [<code>{target_id}</code>] को {duration // 60} मिनट के लिए म्यूट कर दिया गया है।"
        )
    else:
        await message.reply("❌ म्यूट करने में विफलता। बॉट अनुमतियों की जांच करें।")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Restores speech for a muted user."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास यह अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply("⚠️ कृपया यूजर के मैसेज पर रिप्लाई करें या ID दें।")
        return

    success = await ModerationService.unmute_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=target_id,
        admin_id=message.from_user.id,
    )
    if success:
        await message.reply(
            f"🔊 यूजर [<code>{target_id}</code>] को अनम्यूट कर दिया गया है।"
        )
    else:
        await message.reply("❌ अनम्यूट करने में विफलता।")


@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Issues an official warning with automatic escalation."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास चेतावनी (Warning) देने की अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply("⚠️ कृपया चेतावनी देने के लिए यूजर के मैसेज पर रिप्लाई करें।")
        return

    if await is_user_admin(bot, message.chat.id, target_id):
        await message.reply("❌ एडमिन को चेतावनी नहीं दी जा सकती।")
        return

    settings = await get_group_settings(session, message.chat.id)
    reason = "Admin manual warn"
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        reason = parts[1]

    warn_count, escalation = await ModerationService.warn_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=target_id,
        reason=reason,
        admin_id=message.from_user.id,
        settings=settings,
    )

    limit = settings.warn_limit if settings else 3
    if escalation:
        await message.reply(
            f"⚠️ यूजर [<code>{target_id}</code>] को चेतावनी दी गई ({warn_count}/{limit})।\n"
            f"🚨 चेतावनी सीमा पार होने के कारण <b>{escalation.upper()}</b> एक्शन लिया गया।"
        )
    else:
        await message.reply(
            f"⚠️ यूजर [<code>{target_id}</code>] को चेतावनी दी गई!\n"
            f"वर्तमान चेतावनियाँ: <b>{warn_count}/{limit}</b>\n"
            f"कारण: <i>{reason}</i>"
        )


@router.message(Command("warnings"))
async def cmd_warnings(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Checks the warning count of a user."""
    if message.chat.type == "private":
        return

    target_id = _get_target_user(message) or message.from_user.id
    count = await get_warnings_count(session, message.chat.id, target_id)
    settings = await get_group_settings(session, message.chat.id)
    limit = settings.warn_limit if settings else 3
    await message.reply(
        f"ℹ️ यूजर [<code>{target_id}</code>] के पास कुल <b>{count}/{limit}</b> चेतावनियाँ हैं।"
    )


@router.message(Command("resetwarn"))
async def cmd_resetwarn(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Resets warnings for a user."""
    if message.chat.type == "private":
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास यह अनुमति नहीं है।")
        return

    target_id = _get_target_user(message)
    if not target_id:
        await message.reply("⚠️ कृपया यूजर के मैसेज पर रिप्लाई करें।")
        return

    reset_count = await reset_warnings(session, message.chat.id, target_id)
    await message.reply(
        f"✅ यूजर [<code>{target_id}</code>] की सभी {reset_count} चेतावनियाँ रीसेट कर दी गई हैं।"
    )


@router.message(Command("pin"))
async def cmd_pin(message: Message, bot: Bot) -> None:
    """Pins a replied message."""
    if message.chat.type == "private" or not message.reply_to_message:
        await message.reply("⚠️ कृपया पिन करने के लिए किसी मैसेज पर रिप्लाई करें।")
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास मैसेज पिन करने की अनुमति नहीं है।")
        return

    try:
        await bot.pin_chat_message(
            chat_id=message.chat.id, message_id=message.reply_to_message.message_id
        )
        await message.reply("📌 मैसेज सफलतापूर्वक पिन कर दिया गया।")
    except Exception as e:
        await message.reply(f"❌ पिन करने में विफलता: {e}")


@router.message(Command("unpin"))
async def cmd_unpin(message: Message, bot: Bot) -> None:
    """Unpins the currently pinned message."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास यह अनुमति नहीं है।")
        return

    try:
        await bot.unpin_chat_message(chat_id=message.chat.id)
        await message.reply("📌 मैसेज अनपिन कर दिया गया।")
    except Exception as e:
        await message.reply(f"❌ अनपिन करने में विफलता: {e}")


@router.message(Command("logs"))
async def cmd_logs(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Displays recent audit logs for the group."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल ग्रुप एडमिनिस्ट्रेटर लॉग देख सकते हैं।")
        return

    logs = await get_audit_logs(session, message.chat.id, limit=5)
    if not logs:
        await message.reply("📋 इस ग्रुप के लिए अभी कोई ऑडिट लॉग उपलब्ध नहीं है।")
        return

    lines = ["📋 <b>हालिया एडमिन ऑडिट लॉग्स:</b>\n"]
    for l in logs:
        time_str = l.created_at.strftime("%Y-%m-%d %H:%M UTC") if l.created_at else ""
        lines.append(
            f"• <b>{l.action}</b> | कर्ता: <code>{l.actor_id or 'System'}</code> | लक्ष्य: <code>{l.target_id or 'N/A'}</code> ({time_str})"
        )

    await message.reply("\n".join(lines))
