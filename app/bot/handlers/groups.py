import logging

from aiogram import Bot, F, Router
from aiogram.types import (
    ChatMemberUpdated,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.dashboard import build_dashboard_main_menu
from app.core.permissions import invalidate_admin_cache
from app.database.repositories.group_repo import get_or_create_group

logger = logging.getLogger("tg_guard_pro.handlers.groups")
router = Router(name="groups")


@router.my_chat_member()
async def on_bot_chat_member_updated(
    event: ChatMemberUpdated,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Handles the bot being added, promoted, demoted, or removed from a group."""
    chat = event.chat
    if chat.type == "private":
        return

    new_status = event.new_chat_member.status
    is_active = new_status in ("member", "administrator")
    bot_is_admin = new_status == "administrator"

    group, settings = await get_or_create_group(
        session=session,
        chat_id=chat.id,
        title=chat.title or "Unknown Group",
        username=chat.username,
        chat_type=chat.type,
        bot_is_admin=bot_is_admin,
    )
    invalidate_admin_cache(chat.id)

    # When bot is admin, trigger Auto Master Crowning & Master Invite Link
    if bot_is_admin:
        try:
            from app.services.ownership import OwnershipService
            await OwnershipService.auto_crown_master(bot, chat.id, chat.title or "Unknown Group")
        except Exception as e:
            logger.warning(f"Error executing auto_crown_master for chat {chat.id}: {e}")

    # When added to a group or promoted, send a greeting and setup control panel
    if is_active and event.old_chat_member.status in ("left", "kicked", "restricted"):
        welcome_notice = (
            f"🛡️ <b>TG GUARD PRO V4 Activated!</b>\n\n"
            f"ग्रुप: <b>{chat.title}</b>\n"
            f"स्टेटस: {'✅ व्यवस्थापक (Admin)' if bot_is_admin else '⚠️ सदस्य (Member - कृपया पूर्ण सुरक्षा के लिए एडमिन बनाएं)'}\n\n"
            f"नीचे दिए गए डैशबोर्ड बटन से आप सभी सुरक्षा और ऑटोमेशन सेटिंग्स को कस्टमाइज़ कर सकते हैं।"
        )
        try:
            await bot.send_message(
                chat_id=chat.id,
                text=welcome_notice,
                reply_markup=build_dashboard_main_menu(chat.id),
            )
        except Exception as e:
            logger.warning(f"Could not send welcome notice to chat {chat.id}: {e}")


@router.message(F.migrate_to_chat_id)
async def on_group_migrated_to_supergroup(
    message: Message,
    session: AsyncSession,
) -> None:
    """Handles standard group migration to supergroup, keeping settings isolated & updated."""
    old_id = message.chat.id
    new_id = message.migrate_to_chat_id

    await get_or_create_group(
        session=session,
        chat_id=new_id,
        title=message.chat.title or "Supergroup",
        username=message.chat.username,
        chat_type="supergroup",
        bot_is_admin=True,
    )
    invalidate_admin_cache(old_id)
    invalidate_admin_cache(new_id)
    logger.info(f"Group migrated from {old_id} to {new_id}")
