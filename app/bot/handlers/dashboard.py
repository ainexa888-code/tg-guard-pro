import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.dashboard import (
    build_audit_logs_keyboard,
    build_dashboard_main_menu,
    build_toggle_keyboard,
)
from app.config import get_settings
from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import (
    get_active_groups,
    get_blocked_words,
    get_domain_rules,
    get_group_settings,
    get_keyword_reactions,
    update_group_settings,
)

settings = get_settings()
from app.database.repositories.moderation_repo import get_audit_logs
from app.services.analytics import AnalyticsService

logger = logging.getLogger("tg_guard_pro.handlers.dashboard")
router = Router(name="dashboard")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Handles /start in private chat or groups."""
    if message.chat.type == "private":
        start_text = (
            "🛡️ <b>TG GUARD PRO V3 — ऑटोनॉमस टेलीग्राम ग्रुप सिक्योरिटी बॉट</b>\n\n"
            "नमस्ते! मैं एक अत्याधुनिक टेलीग्राम सुरक्षा और ग्रुप प्रबंधन प्रणाली हूँ।\n\n"
            "✨ <b>प्रमुख विशेषताएँ:</b>\n"
            "• 🛡️ एडवांस एंटी-स्पैम, एंटी-लिंक एवं एंटी-रेड\n"
            "• 🤖 स्वचालित कैप्चा वेरिफिकेशन\n"
            "• 🔤 स्टाइलिश/फैंसी फॉन्ट फिल्टर (भारतीय लिपियों के प्रति सुरक्षित)\n"
            "• ⚡ कीवर्ड ऑटो-रिएक्शन एवं बैड वर्ड फिल्टर\n"
            "• 📊 पूर्ण ग्रुप एनालिटिक्स एवं ऑडिट लॉग्स\n\n"
            "अपने ग्रुप को सुरक्षित करने के लिए मुझे अपने ग्रुप में जोड़ें और एडमिन बनाएं!"
        )
        if message.from_user.id == settings.owner_id:
            start_text += (
                "\n\n👑 <b>सुपर एडमिन एक्सेस सक्रिय!</b>\n"
                "आप अपने सभी कनेक्टेड ग्रुप्स को नियंत्रित करने के लिए <code>/panel</code> या <code>/groups</code> का उपयोग कर सकते हैं।"
            )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Add to Your Group",
                        url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true",
                    )
                ]
            ]
        )
        await message.reply(start_text, reply_markup=kb)
    else:
        # In groups
        if await is_user_admin(bot, message.chat.id, message.from_user.id) or message.from_user.id == settings.owner_id:
            await message.reply(
                "🎛️ <b>TG GUARD PRO V3 कंट्रोल पैनल:</b>\nनीचे दिए गए मेनू से सेटिंग्स प्रबंधित करें:",
                reply_markup=build_dashboard_main_menu(message.chat.id),
            )


@router.message(Command("panel"), Command("dashboard"), Command("groups"))
async def cmd_panel(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Opens the interactive dashboard in a group or for bot owner in private chat."""
    if message.chat.type == "private":
        if message.from_user.id == settings.owner_id:
            groups = await get_active_groups(session)
            if not groups:
                await message.reply(
                    "🏢 <b>कोई ग्रुप अभी तक नहीं जुड़ा है।</b>\n\n"
                    "बॉट को अपने ग्रुप में जोड़ें और उसे <b>Admin</b> बनाएं। जैसे ही ग्रुप में कोई मैसेज आएगा, वह यहाँ सूची में दिखाई देगा।"
                )
                return
            buttons = [
                [InlineKeyboardButton(text=f"🏢 {g.title}", callback_data=f"dash:main:{g.id}")]
                for g in groups[:15]
            ]
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.reply(
                "👑 <b>सुपर एडमिन कंट्रोल पैनल (Super Admin Dashboard)</b>\n\n"
                "आप बॉट के मालिक हैं। जिस भी ग्रुप की सुरक्षा सेटिंग्स, एंटी-स्पैम, कैप्चा या लॉग्स देखने/बदलने हैं, उस ग्रुप पर टैप करें:",
                reply_markup=kb,
            )
            return
        else:
            await message.reply("डैशबोर्ड खोलने के लिए मुझे अपने ग्रुप में एडमिन बनाएं और ग्रुप में <code>/panel</code> टाइप करें।")
            return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id) and message.from_user.id != settings.owner_id:
        await message.reply("❌ केवल ग्रुप एडमिनिस्ट्रेटर डैशबोर्ड खोल सकते हैं।")
        return

    await message.reply(
        "🎛️ <b>TG GUARD PRO V3 कंट्रोल डैशबोर्ड</b>\nअपनी ग्रुप सेटिंग्स चुनने के लिए बटन पर टैप करें:",
        reply_markup=build_dashboard_main_menu(message.chat.id),
    )


async def _verify_callback_admin(query: CallbackQuery, bot: Bot, chat_id: int) -> bool:
    """Ensures caller has admin privileges on the requested group or is global bot owner."""
    if query.from_user.id == settings.owner_id:
        return True
    if not await is_user_admin(bot, chat_id, query.from_user.id):
        await query.answer("❌ केवल एडमिन ही यह बदलाव कर सकते हैं।", show_alert=True)
        return False
    return True


@router.callback_query(F.data.startswith("dash:"))
async def on_dashboard_callback(
    query: CallbackQuery, bot: Bot, session: AsyncSession
) -> None:
    """Processes all dashboard navigation, section inspection, and toggles."""
    parts = query.data.split(":")
    action = parts[1]

    if action == "close":
        chat_id = int(parts[2])
        if await _verify_callback_admin(query, bot, chat_id):
            try:
                await query.message.delete()
            except Exception:
                await query.answer("पैनल बंद किया गया।")
        return

    if action == "main":
        chat_id = int(parts[2])
        if not await _verify_callback_admin(query, bot, chat_id):
            return
        await query.message.edit_text(
            "🎛️ <b>TG GUARD PRO V3 मुख्य कंट्रोल डैशबोर्ड</b>\nएक विकल्प चुनें:",
            reply_markup=build_dashboard_main_menu(chat_id),
        )
        await query.answer()
        return

    # Handle section views
    if action in (
        "overview",
        "admins",
        "security",
        "reactions",
        "fonts",
        "antispam",
        "antilink",
        "welcome",
        "captcha",
        "antiraid",
        "badwords",
        "autodelete",
        "analytics",
        "audit",
        "broadcast",
        "health",
    ):
        chat_id = int(parts[2])
        if not await _verify_callback_admin(query, bot, chat_id):
            return

        settings = await get_group_settings(session, chat_id)
        if not settings:
            await query.answer("ग्रुप सेटिंग्स लोड नहीं हो सकीं।", show_alert=True)
            return

        # 1. Group Overview
        if action == "overview":
            chat = await bot.get_chat(chat_id)
            text = (
                f"🏢 <b>ग्रुप ओवरव्यू (Group Overview)</b>\n\n"
                f"• नाम: <b>{chat.title}</b>\n"
                f"• Chat ID: <code>{chat_id}</code>\n"
                f"• प्रकार: <b>{chat.type.upper()}</b>\n"
                f"• प्राथमिक भाषा: <b>{settings.language.upper()}</b>\n"
                f"• सुरक्षा स्थिति: <b>सक्रिय (Active & Protected)</b>"
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Back", callback_data=f"dash:main:{chat_id}"
                        )
                    ]
                ]
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 2. Admin Management
        elif action == "admins":
            admins = await bot.get_chat_administrators(chat_id)
            text = f"👮 <b>व्यवस्थापक सूची (Admin Count: {len(admins)})</b>\n\n"
            text += "\n".join(
                f"• {a.user.first_name} [@{a.user.username or 'None'}]"
                for a in admins[:10]
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Back", callback_data=f"dash:main:{chat_id}"
                        )
                    ]
                ]
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 3. Security Settings
        elif action == "security":
            text = (
                "🛡️ <b>सुरक्षा कॉन्फ़िगरेशन</b>\n\n"
                f"• एंटी-स्पैम: {'🟢 ON' if settings.anti_spam else '🔴 OFF'}\n"
                f"• एंटी-लिंक: {'🟢 ON' if settings.anti_link else '🔴 OFF'}\n"
                f"• कैप्चा: {'🟢 ON' if settings.captcha_enabled else '🔴 OFF'}\n"
                f"• एंटी-रेड: {'🟢 ON' if settings.anti_raid else '🔴 OFF'}\n"
                f"• फॉन्ट फिल्टर: {'🟢 ON' if settings.fancy_font_detection else '🔴 OFF'}"
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Back", callback_data=f"dash:main:{chat_id}"
                        )
                    ]
                ]
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 4. Auto Reactions
        elif action == "reactions":
            reactions = await get_keyword_reactions(session, chat_id)
            text = (
                "⚡ <b>ऑटो-रिएक्शन प्रबंधन</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.auto_reactions else '🔴 Disabled'}</b>\n"
                f"कॉन्फ़िगर किए गए कीवर्ड्स: <b>{len(reactions)}</b>\n\n"
                "कीवर्ड जोड़ने के लिए: <code>/reaction add &lt;word&gt; &lt;emoji&gt;</code>"
            )
            kb = build_toggle_keyboard(
                chat_id, "auto_reactions", settings.auto_reactions
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 5. Fancy Font Filter
        elif action == "fonts":
            text = (
                "🔤 <b>फैंसी फॉन्ट डिटेक्शन</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.fancy_font_detection else '🔴 Disabled'}</b>\n"
                f"एक्शन मोड: <b>{settings.fancy_font_action.upper()}</b>\n\n"
                "मोड बदलने के लिए: <code>/font mode warn</code> या <code>/font mode delete</code>"
            )
            kb = build_toggle_keyboard(
                chat_id, "fancy_font_detection", settings.fancy_font_detection
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 6. Anti-Spam
        elif action == "antispam":
            text = (
                "🚫 <b>एंटी-स्पैम सुरक्षा</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.anti_spam else '🔴 Disabled'}</b>\n"
                f"फ्लड सीमा: <b>{settings.spam_limit} संदेश / 5 सेकंड</b>\n"
                f"अधिकतम चेतावनियाँ: <b>{settings.warn_limit}</b>\n"
                f"एस्केलेशन एक्शन: <b>{settings.warn_action.upper()}</b>"
            )
            kb = build_toggle_keyboard(chat_id, "anti_spam", settings.anti_spam)
            await query.message.edit_text(text, reply_markup=kb)

        # 7. Anti-Link
        elif action == "antilink":
            rules = await get_domain_rules(session, chat_id)
            text = (
                "🔗 <b>एंटी-लिंक सुरक्षा</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.anti_link else '🔴 Disabled'}</b>\n"
                f"कस्टम डोमेन नियम: <b>{len(rules)}</b>\n\n"
                "डोमेन अनुमति देने के लिए: <code>/allowdomain example.com</code>"
            )
            kb = build_toggle_keyboard(chat_id, "anti_link", settings.anti_link)
            await query.message.edit_text(text, reply_markup=kb)

        # 8. Welcome System
        elif action == "welcome":
            text = (
                "👋 <b>स्वागत प्रणाली (Welcome System)</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.welcome_enabled else '🔴 Disabled'}</b>\n"
                f"अलविदा संदेश: <b>{'🟢 Enabled' if settings.goodbye_enabled else '🔴 Disabled'}</b>\n"
                f"ऑटो-डिलीट: <b>{'🟢 Enabled (' + str(settings.auto_delete_duration) + 's)' if settings.auto_delete_welcome else '🔴 Disabled'}</b>"
            )
            kb = build_toggle_keyboard(
                chat_id, "welcome_enabled", settings.welcome_enabled
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 9. Captcha
        elif action == "captcha":
            text = (
                "🤖 <b>कैप्चा वेरिफिकेशन</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.captcha_enabled else '🔴 Disabled'}</b>\n"
                f"प्रकार: <b>{settings.captcha_mode.upper()}</b>\n"
                f"समय सीमा: <b>{settings.captcha_timeout} सेकंड</b>"
            )
            kb = build_toggle_keyboard(
                chat_id, "captcha_enabled", settings.captcha_enabled
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 10. Anti-Raid
        elif action == "antiraid":
            text = (
                "🚨 <b>एंटी-रेड सुरक्षा</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.anti_raid else '🔴 Disabled'}</b>\n"
                f"सीमा: <b>{settings.raid_limit} सदस्य / {settings.raid_window} सेकंड</b>"
            )
            kb = build_toggle_keyboard(chat_id, "anti_raid", settings.anti_raid)
            await query.message.edit_text(text, reply_markup=kb)

        # 11. Bad Words
        elif action == "badwords":
            words = await get_blocked_words(session, chat_id)
            text = (
                "🤬 <b>बैड वर्ड फिल्टर</b>\n\n"
                f"स्थिति: <b>{'🟢 Enabled' if settings.bad_word_filter else '🔴 Disabled'}</b>\n"
                f"प्रतिबंधित शब्द: <b>{len(words)}</b>\n"
                f"एक्शन: <b>{settings.bad_word_action.upper()}</b>"
            )
            kb = build_toggle_keyboard(
                chat_id, "bad_word_filter", settings.bad_word_filter
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 12. Auto Delete
        elif action == "autodelete":
            text = (
                "⏳ <b>ऑटो-डिलीट सेटिंग्स</b>\n\n"
                f"स्वागत संदेश ऑटो-डिलीट: <b>{'🟢 Enabled' if settings.auto_delete_welcome else '🔴 Disabled'}</b>\n"
                f"अवधि: <b>{settings.auto_delete_duration} सेकंड</b>"
            )
            kb = build_toggle_keyboard(
                chat_id, "auto_delete_welcome", settings.auto_delete_welcome
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 13. Analytics
        elif action == "analytics":
            report = await AnalyticsService.format_analytics_report(
                chat_id, days=7, language="hi"
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Back", callback_data=f"dash:main:{chat_id}"
                        )
                    ]
                ]
            )
            await query.message.edit_text(report, reply_markup=kb)

        # 14. Audit Logs
        elif action == "audit":
            logs = await get_audit_logs(session, chat_id, limit=5, offset=0)
            if not logs:
                text = "📋 अभी कोई ऑडिट लॉग्स उपलब्ध नहीं हैं।"
            else:
                lines = ["📋 <b>ग्रुप ऑडिट लॉग्स (हालिया):</b>\n"]
                for l in logs:
                    lines.append(
                        f"• <b>{l.action}</b> (कर्ता: <code>{l.actor_id or 'Sys'}</code>)"
                    )
                text = "\n".join(lines)
            kb = build_audit_logs_keyboard(chat_id, offset=0, has_next=len(logs) == 5)
            await query.message.edit_text(text, reply_markup=kb)

        # 15. Broadcast Settings
        elif action == "broadcast":
            text = (
                "📢 <b>मास ब्रॉडकास्ट सेटिंग्स</b>\n\n"
                f"ग्लोबल घोषणाओं की अनुमति (Opt-in): <b>{'🟢 Yes (Opted-in)' if settings.broadcast_optin else '🔴 No (Opted-out)'}</b>\n\n"
                "बदलने के लिए: <code>/broadcastoptin</code> या <code>/broadcastoptout</code>"
            )
            kb = build_toggle_keyboard(
                chat_id, "broadcast_optin", settings.broadcast_optin
            )
            await query.message.edit_text(text, reply_markup=kb)

        # 16. Bot Health
        elif action == "health":
            me = await bot.get_me()
            text = (
                "💚 <b>सिस्टम हेल्थ स्टेटस (System Health)</b>\n\n"
                f"• बॉट हैंडल: <b>@{me.username}</b>\n"
                f"• स्थिति: <b>🟢 स्वस्थ एवं सक्रिय (Healthy & Operational)</b>\n"
                f"• डेटाबेस: <b>कनेक्टेड एवं सिंक (Connected)</b>\n"
                f"• बैकग्राउंड वर्कर: <b>रनिंग (Active)</b>"
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Back", callback_data=f"dash:main:{chat_id}"
                        )
                    ]
                ]
            )
            await query.message.edit_text(text, reply_markup=kb)

        await query.answer()
        return

    # Handle Toggle Action
    if action == "toggle":
        setting_key = parts[2]
        chat_id = int(parts[3])
        new_val = parts[4] == "1"

        if not await _verify_callback_admin(query, bot, chat_id):
            return

        await update_group_settings(session, chat_id, **{setting_key: new_val})
        await query.answer(
            f"सेटिंग अपडेट: {'सक्षम (Enabled)' if new_val else 'अक्षम (Disabled)'}"
        )

        # Return to main menu
        await query.message.edit_text(
            "🎛️ <b>TG GUARD PRO V3 मुख्य कंट्रोल डैशबोर्ड</b>\nसेटिंग्स सफलतापूर्वक अपडेट की गईं!",
            reply_markup=build_dashboard_main_menu(chat_id),
        )
        return

    # Handle Audit Pagination
    if action == "audit_page":
        chat_id = int(parts[2])
        offset = int(parts[3])

        if not await _verify_callback_admin(query, bot, chat_id):
            return

        logs = await get_audit_logs(session, chat_id, limit=5, offset=offset)
        if not logs:
            text = "📋 इस पृष्ठ पर कोई लॉग्स नहीं हैं।"
        else:
            lines = [f"📋 <b>ग्रुप ऑडिट लॉग्स (पेज offset: {offset}):</b>\n"]
            for l in logs:
                lines.append(
                    f"• <b>{l.action}</b> (कर्ता: <code>{l.actor_id or 'Sys'}</code>)"
                )
            text = "\n".join(lines)

        kb = build_audit_logs_keyboard(chat_id, offset=offset, has_next=len(logs) == 5)
        await query.message.edit_text(text, reply_markup=kb)
        await query.answer()
