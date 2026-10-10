import logging

from aiogram import Bot, F, Router
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import (
    get_group_settings,
    update_group_settings,
)
from app.services.analytics import AnalyticsService
from app.services.captcha import CaptchaService

logger = logging.getLogger("tg_guard_pro.handlers.captcha")
router = Router(name="captcha")


@router.message(Command("captcha"))
async def cmd_captcha(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Manages member verification captcha."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही कैप्चा सेटिंग्स बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "🤖 <b>कैप्चा वेरिफिकेशन कमांड्स:</b>\n\n"
            "• <code>/captcha on</code> — कैप्चा चालू करें\n"
            "• <code>/captcha off</code> — कैप्चा बंद करें\n"
            "• <code>/captcha timeout 120</code> — टाइमआउट समय (सेकंड) सेट करें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, captcha_enabled=True)
        await message.reply("✅ नए सदस्यों के लिए कैप्चा वेरिफिकेशन चालू (ON) कर दिया गया है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, captcha_enabled=False)
        await message.reply("🛑 कैप्चा वेरिफिकेशन बंद (OFF) कर दिया गया है।")
    elif action == "timeout" and len(parts) > 2 and parts[2].isdigit():
        sec = int(parts[2])
        await update_group_settings(session, message.chat.id, captcha_timeout=sec)
        await message.reply(f"✅ कैप्चा टाइमआउट <b>{sec} सेकंड</b> पर सेट किया गया।")


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def enforce_captcha_on_join(
    event: ChatMemberUpdated, bot: Bot, session: AsyncSession
) -> None:
    """Challenges newly joined users with verification."""
    if event.chat.type == "private" or event.new_chat_member.user.is_bot:
        return

    settings = await get_group_settings(session, event.chat.id)
    if not settings or not settings.captcha_enabled:
        return

    user = event.new_chat_member.user
    try:
        challenge_id, correct_ans, kb = await CaptchaService.create_and_restrict(
            bot=bot,
            session=session,
            chat_id=event.chat.id,
            user_id=user.id,
            mode=settings.captcha_mode,
            timeout_seconds=settings.captcha_timeout,
        )

        prompt_text = (
            f"🛡️ <b>सुरक्षा वेरिफिकेशन (Captcha Verification)</b>\n\n"
            f"स्वागत है {user.mention_html()}! ग्रुप में मैसेज भेजने के लिए कृपया नीचे दिए गए सही विकल्प पर क्लिक करके सत्यापित करें:"
        )
        await bot.send_message(
            chat_id=event.chat.id,
            text=prompt_text,
            reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"Error imposing captcha: {e}")


@router.callback_query(F.data.startswith("cpt:"))
async def on_captcha_callback(
    query: CallbackQuery, bot: Bot, session: AsyncSession
) -> None:
    """Handles captcha button selection."""
    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer("अमान्य अनुरोध।", show_alert=True)
        return

    challenge_id = parts[1]
    submitted_answer = parts[2]
    user_id = query.from_user.id

    is_success, msg = await CaptchaService.verify_answer(
        bot=bot,
        session=session,
        challenge_id=challenge_id,
        user_id=user_id,
        submitted_answer=submitted_answer,
    )

    if is_success:
        await AnalyticsService.record_event(
            query.message.chat.id, "captcha_success_count", 1
        )
        await query.answer("✅ वेरिफिकेशन सफल! आपका स्वागत है।", show_alert=True)
        try:
            await query.message.edit_text(
                f"✅ {query.from_user.mention_html()} ने सफलतापूर्वक वेरिफिकेशन पूरा कर लिया है।"
            )
        except Exception:
            pass
    else:
        await AnalyticsService.record_event(
            query.message.chat.id, "captcha_failed_count", 1
        )
        await query.answer(f"❌ {msg}", show_alert=True)
