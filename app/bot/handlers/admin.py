import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import ChatMemberOwner, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import can_user_moderate, is_user_admin
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
