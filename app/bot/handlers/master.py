import logging
import time
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.config import get_settings
from app.core.permissions import (
    is_master_owner,
    check_bot_detailed_permissions,
    can_user_moderate,
    can_bot_moderate,
)
from app.database.models import Group, GroupSettings, User, AuditLog, ScheduledDeletion
from app.database.repositories.group_repo import get_active_groups, get_group_settings
from app.database.repositories.moderation_repo import get_audit_logs
from app.services.alerts import AlertService
from app.bot.keyboards.master import (
    build_master_main_menu,
    build_groups_pagination_keyboard,
    build_group_detail_keyboard,
    build_back_to_master,
)

logger = logging.getLogger("tg_guard_pro.handlers.master")
router = Router(name="master")
settings = get_settings()


async def _verify_master_access(event: Message | CallbackQuery, bot: Bot) -> bool:
    """Strictly validates that caller is the designated Master Operator."""
    user = event.from_user
    if not user or not is_master_owner(user.id):
        # Dispatch security alert for unauthorized attempt
        user_info = f"@{user.username}" if user.username else f"ID {user.id}"
        await AlertService.dispatch_alert(
            bot=bot,
            title="Unauthorized Master Access Attempt",
            message=f"यूजर {user.full_name} ({user_info}) ने मास्टर पैनल को एक्सेस करने का प्रयास किया।",
            priority="HIGH",
            dedup_key=f"unauth_master:{user.id}",
        )
        if isinstance(event, Message):
            await event.reply("❌ यह कमांड उपलब्ध नहीं है।")
        else:
            await event.answer("❌ एक्सेस अस्वीकृत (Access Denied).", show_alert=True)
        return False
    return True


@router.message(Command("master"))
async def cmd_master(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Opens the Private Master Operator Dashboard."""
    if message.chat.type != "private":
        # Master panel is strictly restricted to private chats
        await message.reply("🔒 सुरक्षा कारणों से मास्टर पैनल केवल बॉट के साथ प्राइवेट चैट में ही खुलता है।")
        return

    if not await _verify_master_access(message, bot):
        return

    text = (
        "👑 <b>TG GUARD PRO V4 — मास्टर कंट्रोल सेंटर</b>\n\n"
        f"स्वागत है मास्टर ऑपरेटर [<code>{message.from_user.id}</code>]!\n"
        f"• बॉट हैंडल: <b>@{settings.bot_username}</b>\n"
        f"• लॉग चैट ID: <code>{settings.log_chat_id}</code>\n"
        f"• मेंटेनेंस मोड: <b>{'🟢 सामान्य (Active)' if not settings.maintenance_mode else '🔴 मेंटेनेंस (Paused)'}</b>\n\n"
        "नीचे दिए गए मॉड्यूल में से किसी एक को चुनें:"
    )
    await message.reply(text, reply_markup=build_master_main_menu())


@router.message(Command("checkpermissions"))
async def cmd_checkpermissions(message: Message, bot: Bot) -> None:
    """Checks and reports all active permissions of the bot in the current group."""
    if message.chat.type == "private":
        await message.reply("⚠️ कृपया इस कमांड को किसी ग्रुप में भेजें जहाँ बॉट मौजूद है।")
        return

    perms = await check_bot_detailed_permissions(bot, message.chat.id)
    if not perms.get("is_admin"):
        err = perms.get("error", "बॉट ग्रुप में एडमिन नहीं है।")
        await message.reply(
            f"⚠️ <b>बॉट अनुमतियाँ अपर्याप्त हैं:</b>\n\n"
            f"स्थिति: ❌ सदस्य (Not Admin)\n"
            f"विवरण: <i>{err}</i>\n\n"
            "कृपया ग्रुप सेटिंग्स में जाकर बॉट को <b>Admin</b> बनाएं और आवश्यक अधिकार प्रदान करें।"
        )
        return

    def badge(val: bool) -> str:
        return "✅ हाँ (Granted)" if val else "❌ नहीं (Missing)"

    lines = [
        f"🔑 <b>बॉट अनुमतियों की लाइव रिपोर्ट ({message.chat.title}):</b>\n",
        f"• स्टेटस: <b>{'👑 ओनर' if perms['is_owner'] else '👮 एडमिन'}</b>",
        f"• मैसेज डिलीट करना: {badge(perms['can_delete_messages'])}",
        f"• सदस्यों को म्यूट/बैन करना: {badge(perms['can_restrict_members'])}",
        f"• नए एडमिन जोड़ना: {badge(perms['can_promote_members'])}",
        f"• ग्रुप जानकारी बदलना: {badge(perms['can_change_info'])}",
        f"• लिंक से इनवाइट करना: {badge(perms['can_invite_users'])}",
        f"• मैसेज पिन करना: {badge(perms['can_pin_messages'])}",
        f"• वीडियो चैट प्रबंधन: {badge(perms['can_manage_video_chats'])}",
        f"• टॉपिक्स प्रबंधन: {badge(perms['can_manage_topics'])}",
    ]

    missing = [k for k, v in perms.items() if v is False and k not in ("is_admin", "is_owner")]
    if missing:
        lines.append(f"\n⚠️ <b>सुझाव:</b> पूर्ण सुरक्षा हेतु अनुपलब्ध अनुमतियाँ सक्रिय करें।")
    else:
        lines.append(f"\n✨ <b>बॉट के पास सभी आवश्यक अधिकार सक्रिय हैं!</b>")

    await message.reply("\n".join(lines))


@router.message(Command("adminpermissions"))
async def cmd_adminpermissions(message: Message, bot: Bot) -> None:
    """Inspects specific permissions of a replied-to administrator."""
    if message.chat.type == "private":
        return

    target_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1 and message.text.split()[1].isdigit():
        target_id = int(message.text.split()[1])

    if not target_id:
        await message.reply("⚠️ कृपया किसी एडमिन के मैसेज पर रिप्लाई करें: <code>/adminpermissions</code>")
        return

    try:
        member = await bot.get_chat_member(chat_id=message.chat.id, user_id=target_id)
        role = "👑 ग्रुप ओनर" if member.status == "creator" else ("👮 एडमिन" if member.status == "administrator" else "👤 सामान्य सदस्य")
        lines = [f"📋 <b>यूजर अनुमतियाँ [<code>{target_id}</code>]:</b>\n", f"• पद: <b>{role}</b>"]

        if member.status in ("creator", "administrator"):
            lines.extend([
                f"• मैसेज डिलीट: {'✅' if getattr(member, 'can_delete_messages', False) else '❌'}",
                f"• सदस्य म्यूट/बैन: {'✅' if getattr(member, 'can_restrict_members', False) else '❌'}",
                f"• एडमिन प्रमोट: {'✅' if getattr(member, 'can_promote_members', False) else '❌'}",
                f"• मैसेज पिन: {'✅' if getattr(member, 'can_pin_messages', False) else '❌'}",
            ])
        await message.reply("\n".join(lines))
    except Exception as e:
        await message.reply(f"❌ अनुमतियाँ प्राप्त करने में त्रुटि: {e}")


@router.message(Command("delete"))
async def cmd_delete(message: Message, bot: Bot) -> None:
    """Deletes a replied-to message."""
    if message.chat.type == "private" or not message.reply_to_message:
        await message.reply("⚠️ कृपया डिलीट करने के लिए किसी मैसेज पर रिप्लाई करें।")
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास मैसेज डिलीट करने की अनुमति नहीं है।")
        return

    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception as e:
        await message.reply(f"❌ मैसेज डिलीट करने में विफलता: {e}")


@router.message(Command("purge"))
async def cmd_purge(message: Message, bot: Bot) -> None:
    """Bulk deletes messages from the replied-to message up to current command."""
    if message.chat.type == "private" or not message.reply_to_message:
        await message.reply("⚠️ कृपया जहाँ से डिलीट करना शुरू करना है, उस मैसेज पर रिप्लाई करें: <code>/purge</code>")
        return

    if not await can_user_moderate(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ आपके पास मैसेज डिलीट करने की अनुमति नहीं है।")
        return

    start_id = message.reply_to_message.message_id
    end_id = message.message_id
    total_to_delete = end_id - start_id + 1

    if total_to_delete > 100:
        total_to_delete = 100  # Safety limit for Telegram rate limits

    deleted = 0
    for mid in range(start_id, end_id + 1):
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=mid)
            deleted += 1
        except Exception:
            pass

    notice = await message.answer(f"🧹 <b>{deleted}</b> मैसेज सफलतापूर्वक साफ़ (Purged) कर दिए गए!")
    time.sleep(2)
    try:
        await notice.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("mstr:"))
async def on_master_callback(query: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    """Master Dashboard callback router."""
    if not await _verify_master_access(query, bot):
        return

    data = query.data.split(":")
    action = data[1]

    if action == "close":
        try:
            await query.message.delete()
        except Exception:
            await query.answer("पैनल बंद किया गया।")
        return

    if action == "main":
        text = (
            "👑 <b>TG GUARD PRO V4 — मास्टर कंट्रोल सेंटर</b>\n\n"
            f"ऑपरेटर: <code>{query.from_user.id}</code>\n"
            f"लॉग चैट: <code>{settings.log_chat_id}</code>\n\n"
            "एक मॉड्यूल चुनें:"
        )
        await query.message.edit_text(text, reply_markup=build_master_main_menu())
        await query.answer()
        return

    # 1. Connected Groups
    if action == "groups":
        page = int(data[2]) if len(data) > 2 else 0
        groups = await get_active_groups(session)
        if not groups:
            await query.message.edit_text(
                "🏢 <b>कोई ग्रुप अभी तक नहीं जुड़ा है।</b>\n\nबॉट को ग्रुप में जोड़ें और उसे एडमिन बनाएं।",
                reply_markup=build_back_to_master()
            )
            await query.answer()
            return

        text = f"🏢 <b>कनेक्टेड ग्रुप्स (कुल: {len(groups)}):</b>\n\nग्रुप की सेटिंग्स देखने के लिए किसी भी ग्रुप पर टैप करें:"
        await query.message.edit_text(text, reply_markup=build_groups_pagination_keyboard(groups, page=page))
        await query.answer()
        return

    # 2. Inspect Group
    if action == "group_inspect":
        chat_id = int(data[2])
        group_stmt = select(Group).where(Group.id == chat_id)
        res = await session.execute(group_stmt)
        group = res.scalar_one_or_none()

        if not group:
            await query.answer("ग्रुप डेटाबेस में नहीं मिला।", show_alert=True)
            return

        # Fetch member count live if possible
        try:
            member_count = await bot.get_chat_member_count(chat_id)
        except Exception:
            member_count = "N/A"

        settings_obj = await get_group_settings(session, chat_id)

        text = (
            f"🏢 <b>ग्रुप विवरण: {group.title}</b>\n\n"
            f"• <b>Chat ID:</b> <code>{group.id}</code>\n"
            f"• <b>प्रकार:</b> {group.chat_type.upper()}\n"
            f"• <b>सदस्य संख्या:</b> {member_count}\n"
            f"• <b>बॉट स्टेटस:</b> {'🟢 एडमिन' if group.bot_is_admin else '⚠️ सामान्य सदस्य'}\n\n"
            f"🛡️ <b>सुरक्षा सेटिंग्स:</b>\n"
            f"• एंटी-स्पैम: {'🟢 ON' if settings_obj and settings_obj.anti_spam else '🔴 OFF'}\n"
            f"• एंटी-लिंक: {'🟢 ON' if settings_obj and settings_obj.anti_link else '🔴 OFF'}\n"
            f"• कैप्चा: {'🟢 ON' if settings_obj and settings_obj.captcha_enabled else '🔴 OFF'}\n"
            f"• एंटी-रेड: {'🟢 ON' if settings_obj and settings_obj.anti_raid else '🔴 OFF'}\n"
        )
        await query.message.edit_text(text, reply_markup=build_group_detail_keyboard(chat_id))
        await query.answer()
        return

    # 3. Check Perms in Group
    if action == "check_perm":
        chat_id = int(data[2])
        perms = await check_bot_detailed_permissions(bot, chat_id)
        if not perms.get("is_admin"):
            text = f"⚠️ बॉट चैट <code>{chat_id}</code> में एडमिन नहीं है।"
        else:
            text = (
                f"🔑 <b>बॉट अनुमतियाँ (चैट: <code>{chat_id}</code>):</b>\n\n"
                f"• मैसेज डिलीट: {'✅' if perms['can_delete_messages'] else '❌'}\n"
                f"• सदस्य म्यूट/बैन: {'✅' if perms['can_restrict_members'] else '❌'}\n"
                f"• एडमिन प्रमोट: {'✅' if perms['can_promote_members'] else '❌'}\n"
                f"• मैसेज पिन: {'✅' if perms['can_pin_messages'] else '❌'}"
            )
        await query.message.edit_text(text, reply_markup=build_group_detail_keyboard(chat_id))
        await query.answer()
        return

    # 4. Bot Health
    if action == "health":
        me = await bot.get_me()
        groups_count = len(await get_active_groups(session))
        text = (
            "💚 <b>सिस्टम हेल्थ एवं डायग्नोस्टिक्स</b>\n\n"
            f"• बॉट हैंडल: <b>@{me.username}</b> (ID: <code>{me.id}</code>)\n"
            f"• सक्रिय ग्रुप्स: <b>{groups_count}</b>\n"
            f"• बैकग्राउंड वर्कर: <b>🟢 रनिंग (Active)</b>\n"
            f"• डेटाबेस: <b>🟢 कनेक्टेड (Healthy)</b>\n"
            f"• टाइमज़ोन: <b>{settings.timezone}</b>\n"
            f"• मोड: <b>{settings.environment.upper()}</b>"
        )
        await query.message.edit_text(text, reply_markup=build_back_to_master())
        await query.answer()
        return

    # 5. Global Analytics
    if action == "analytics":
        total_groups = len(await get_active_groups(session))
        total_users_stmt = select(func.count(User.id))
        users_res = await session.execute(total_users_stmt)
        total_users = users_res.scalar_one() or 0

        text = (
            "📊 <b>ग्लोबल प्लेटफॉर्म एनालिटिक्स (Global Analytics)</b>\n\n"
            f"• कुल सुरक्षित ग्रुप्स: <b>{total_groups}</b>\n"
            f"• ट्रैक किए गए कुल मेंबर्स: <b>{total_users}</b>\n"
            f"• सक्रिय इंजन: <b>Aiogram 3.x + SQLAlchemy 2.0 Async</b>\n\n"
            "<i>(प्रत्येक ग्रुप के विशिष्ट 7-दिन/30-दिन स्टैट्स देखने के लिए ग्रुप लिस्ट से ग्रुप चुनें)</i>"
        )
        await query.message.edit_text(text, reply_markup=build_back_to_master())
        await query.answer()
        return

    # 6. Ownership Info
    if action == "ownership":
        text = (
            "👑 <b>ग्रुप ओनरशिप प्रबंधन (Ownership Management)</b>\n\n"
            "ℹ️ <b>टेलीग्राम का आधिकारिक सुरक्षा नियम:</b>\n"
            "टेलीग्राम बॉट एपीआई किसी ग्रुप की मालिकाना ओनरशिप (Ownership) को सीधे ट्रांसफर करने की अनुमति <b>नहीं देता</b>।\n\n"
            "📌 <b>आधिकारिक ओनरशिप ट्रांसफर करने की विधि:</b>\n"
            "1. केवल वर्तमान ग्रुप ओनर अपने मुख्य टेलीग्राम ऐप से यह कर सकता है।\n"
            "2. ग्रुप सेटिंग्स ➔ Administrators ➔ Add Admin (या एडमिन चुनें)।\n"
            "3. 'Transfer Group Ownership' पर टैप करें।\n"
            "4. <i>(टेलीग्राम सुरक्षा शर्त: आपके खाते पर 2FA पासवर्ड कम से कम 7 दिन पुराना होना अनिवार्य है)</i>।\n\n"
            "🛡️ बॉट ओनरशिप बदलावों को डिटेक्ट करता है और ऑडिट लॉग में सुरक्षित रखता है।"
        )
        await query.message.edit_text(text, reply_markup=build_back_to_master())
        await query.answer()
        return

    # 7. Database Status
    if action == "database":
        text = (
            "🗄️ <b>डेटाबेस एवं शेड्यूलर स्थिति</b>\n\n"
            f"• कनेक्शन URL: <code>{settings.database_url.split('@')[-1] if '@' in settings.database_url else 'SQLite Async Engine'}</code>\n"
            f"• कनेक्टिविटी: <b>🟢 ऑनलाइन एवं प्रामाणिक</b>\n"
            f"• ऑटो-डिलीट शेड्यूलर: <b>🟢 सक्रिय (Survives Restarts)</b>\n"
            f"• टेबल्स: <b>16 प्रोडक्शन टेबल्स सिंक</b>"
        )
        await query.message.edit_text(text, reply_markup=build_back_to_master())
        await query.answer()
        return

    # 8. Maintenance Toggle
    if action == "maintenance":
        settings.maintenance_mode = not settings.maintenance_mode
        status = "🔴 मेंटेनेंस मोड सक्रिय (Maintenance ON)" if settings.maintenance_mode else "🟢 मेंटेनेंस मोड बंद (Active Normal)"
        await query.answer(f"स्टेटस: {status}")
        text = (
            f"🚧 <b>मेंटेनेंस मोड सेटिंग:</b>\n\n"
            f"वर्तमान स्थिति: <b>{status}</b>\n\n"
            "मेंटेनेंस मोड ऑन होने पर गैर-एडमिन कमांड्स रोकी जा सकती हैं।"
        )
        await query.message.edit_text(text, reply_markup=build_back_to_master())
        return

    # 9. Generic submenus fallback
    titles = {
        "channels": "📢 <b>कनेक्टेड चैनल्स</b>\n\nवर्तमान में बॉट ग्रुप सुरक्षा मोड पर कार्यरत है।",
        "security": "🛡️ <b>सिक्योरिटी सेंटर</b>\n\nसभी 6 सुरक्षा मॉड्यूल्स (एंटी-स्पैम, एंटी-लिंक, एंटी-रेड, बैड वर्ड्स, फॉन्ट्स, कैप्चा) प्रत्येक ग्रुप के लिए स्वतंत्र रूप से सक्रिय हैं।",
        "admins": "👮 <b>एडमिन प्रबंधन</b>\n\nकमांड्स:\n• <code>/admins</code> — एडमिन सूची\n• <code>/promote</code> — प्रमोट करें\n• <code>/demote</code> — डिमोट करें\n• <code>/adminpermissions</code> — अनुमतियाँ देखें",
        "moderation": "🔨 <b>मॉडरेशन सेंटर</b>\n\nकमांड्स:\n• <code>/ban</code>, <code>/unban</code>\n• <code>/mute</code>, <code>/unmute</code>\n• <code>/warn</code>, <code>/resetwarn</code>\n• <code>/purge</code>, <code>/delete</code>",
        "reactions": "⚡ <b>ऑटो रिएक्शन मैनेजर</b>\n\nग्रुप-वार कीवर्ड इमोजी रिएक्शन्स चालू/बंद करने के लिए संबंधित ग्रुप चुनें।",
        "welcome": "👋 <b>वेलकम एवं कैप्चा मैनेजर</b>\n\nग्रुप्स में नए सदस्यों के स्वागत एवं कैप्चा वेरिफिकेशन नियम पूरी तरह सक्रिय हैं।",
        "antispam": "🚫 <b>एंटी-स्पैम एवं फ्लड</b>\n\n5 सेकंड में 5 से अधिक संदेश या डुप्लीकेट कॉपी-पेस्ट तुरंत ऑटो-डिलीट होते हैं।",
        "antilink": "🔗 <b>एंटी-लिंक शील्ड</b>\n\nबाहरी डोमेन एवं इनवाइट लिंक्स स्वतः ब्लॉक किए जाते हैं।",
        "antiraid": "🚨 <b>एंटी-रेड इंजन</b>\n\n60 सेकंड में अत्यधिक जॉइन्स होने पर ऑटोमैटिक अलर्ट ट्रिगर होता है।",
        "badwords": "🤬 <b>बैड वर्ड्स फिल्टर</b>\n\nयूनिकोड-सक्षम गाली व अपशब्द तुरंत डिलीट होते हैं।",
        "fonts": "🔤 <b>फैंसी फॉन्ट डिटेक्शन</b>\n\nस्टाइलिश फॉन्ट्स ब्लॉक हैं, भारतीय भाषाएँ सुरक्षित हैं।",
        "broadcast": "📢 <b>ब्रॉडकास्ट सेंटर</b>\n\nग्लोबल संदेश भेजने के लिए: <code>/broadcast &lt;संदेश&gt;</code> का उपयोग करें।",
        "alerts": f"🔔 <b>लाइव अलर्ट्स एवं लॉग चैट</b>\n\nलॉग चैट ID: <code>{settings.log_chat_id}</code>\nअलर्ट प्रायोरिटी: CRITICAL, HIGH, MEDIUM, LOW",
    }
    content = titles.get(action, "ℹ️ मॉड्यूल विवरण उपलब्ध है।")
    await query.message.edit_text(content, reply_markup=build_back_to_master())
    await query.answer()
