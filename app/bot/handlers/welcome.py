import logging

from aiogram import Bot, Router
from aiogram.filters import (
    JOIN_TRANSITION,
    LEAVE_TRANSITION,
    ChatMemberUpdatedFilter,
    Command,
)
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.core.security import sanitize_telegram_html
from app.database.repositories.group_repo import (
    get_group_settings,
    update_group_settings,
)
from app.services.analytics import AnalyticsService
from app.services.scheduler import SchedulerService

logger = logging.getLogger("tg_guard_pro.handlers.welcome")
router = Router(name="welcome")


@router.message(Command("welcome"))
async def cmd_welcome(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Toggles welcome message."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "• <code>/welcome on</code> — चालू करें\n• <code>/welcome off</code> — बंद करें\n• <code>/setwelcome &lt;text&gt;</code> — संदेश सेट करें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, welcome_enabled=True)
        await message.reply("✅ स्वागत संदेश (Welcome) चालू कर दिया गया है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, welcome_enabled=False)
        await message.reply("🛑 स्वागत संदेश (Welcome) बंद कर दिया गया है।")


@router.message(Command("setwelcome"))
async def cmd_setwelcome(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Sets custom welcome message."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "⚠️ कृपया स्वागत संदेश लिखें: <code>/setwelcome Welcome {name} to {title}!</code>"
        )
        return

    text = parts[1]
    await update_group_settings(session, message.chat.id, welcome_text=text)
    await message.reply("✅ नया स्वागत संदेश सफलतापूर्वक सुरक्षित कर लिया गया है।")


@router.message(Command("goodbye"))
async def cmd_goodbye(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Toggles goodbye message."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "• <code>/goodbye on</code> — चालू करें\n• <code>/goodbye off</code> — बंद करें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, goodbye_enabled=True)
        await message.reply("✅ अलविदा संदेश (Goodbye) चालू कर दिया गया है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, goodbye_enabled=False)
        await message.reply("🛑 अलविदा संदेश (Goodbye) बंद कर दिया गया है।")


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_user_join(
    event: ChatMemberUpdated, bot: Bot, session: AsyncSession
) -> None:
    """Sends greeting when new member joins."""
    if event.chat.type == "private" or event.new_chat_member.user.is_bot:
        return

    await AnalyticsService.record_event(event.chat.id, "joins_count", 1)

    settings = await get_group_settings(session, event.chat.id)
    if not settings or not settings.welcome_enabled:
        return

    user = event.new_chat_member.user
    tpl = settings.welcome_text or "Welcome {name} to {title}!"
    welcome_text = (
        tpl.replace("{name}", user.mention_html())
        .replace("{title}", sanitize_telegram_html(event.chat.title or "Group"))
        .replace("{id}", str(user.id))
        .replace("{username}", f"@{user.username}" if user.username else "")
    )

    try:
        sent_msg = await bot.send_message(chat_id=event.chat.id, text=welcome_text)
        if settings.auto_delete_welcome:
            scheduler = SchedulerService(bot)
            await scheduler.schedule_auto_delete(
                chat_id=event.chat.id,
                message_id=sent_msg.message_id,
                delay_seconds=settings.auto_delete_duration,
                reason="welcome_auto_delete",
            )
    except Exception as e:
        logger.warning(f"Could not send welcome message: {e}")


@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def on_user_leave(
    event: ChatMemberUpdated, bot: Bot, session: AsyncSession
) -> None:
    """Sends notice when a member leaves."""
    if event.chat.type == "private" or event.old_chat_member.user.is_bot:
        return

    await AnalyticsService.record_event(event.chat.id, "leaves_count", 1)

    settings = await get_group_settings(session, event.chat.id)
    if not settings or not settings.goodbye_enabled:
        return

    user = event.old_chat_member.user
    tpl = settings.goodbye_text or "Goodbye {name}!"
    goodbye_text = tpl.replace("{name}", user.full_name).replace(
        "{title}", sanitize_telegram_html(event.chat.title or "Group")
    )

    try:
        await bot.send_message(chat_id=event.chat.id, text=goodbye_text)
    except Exception as e:
        logger.warning(f"Could not send goodbye message: {e}")
