import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_user_admin
from app.database.repositories.group_repo import (
    add_domain_rule,
    get_domain_rules,
    get_group_settings,
    update_group_settings,
)
from app.services.analytics import AnalyticsService
from app.services.antilink import check_link_violation, extract_domains_and_links
from app.services.moderation import ModerationService

logger = logging.getLogger("tg_guard_pro.handlers.antilink")
router = Router(name="antilink")


@router.message(Command("antilink"))
async def cmd_antilink(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Toggles anti-link protection."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर ही एंटी-लिंक सेटिंग्स बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply(
            "🔗 <b>एंटी-लिंक कमांड्स:</b>\n\n"
            "• <code>/antilink on</code> — एंटी-लिंक सुरक्षा चालू करें\n"
            "• <code>/antilink off</code> — एंटी-लिंक सुरक्षा बंद करें\n"
            "• <code>/allowdomain example.com</code> — डोमेन को अनुमति दें\n"
            "• <code>/blockdomain example.com</code> — डोमेन को ब्लॉक करें\n"
            "• <code>/allowlist</code> — अनुमति प्राप्त डोमेन देखें"
        )
        return

    action = parts[1].lower()
    if action == "on":
        await update_group_settings(session, message.chat.id, anti_link=True)
        await message.reply("✅ एंटी-लिंक सुरक्षा चालू (ON) कर दी गई है।")
    elif action == "off":
        await update_group_settings(session, message.chat.id, anti_link=False)
        await message.reply("🛑 एंटी-लिंक सुरक्षा बंद (OFF) कर दी गई है।")


@router.message(Command("allowdomain"))
async def cmd_allowdomain(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Adds a domain to allowlist."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply("⚠️ कृपया डोमेन नाम दें: <code>/allowdomain youtube.com</code>")
        return

    domain = parts[1]
    await add_domain_rule(session, message.chat.id, domain, rule_type="allow")
    await message.reply(
        f"✅ डोमेन <code>{domain}</code> को अनुमति सूची (Allowlist) में जोड़ दिया गया है।"
    )


@router.message(Command("blockdomain"))
async def cmd_blockdomain(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Adds a domain to blocklist."""
    if message.chat.type == "private":
        return

    if not await is_user_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("❌ केवल एडमिनिस्ट्रेटर यह सेटिंग बदल सकते हैं।")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.reply("⚠️ कृपया डोमेन नाम दें: <code>/blockdomain spamlink.xyz</code>")
        return

    domain = parts[1]
    await add_domain_rule(session, message.chat.id, domain, rule_type="block")
    await message.reply(
        f"🚫 डोमेन <code>{domain}</code> को ब्लॉक सूची (Blocklist) में जोड़ दिया गया है।"
    )


@router.message(Command("allowlist"))
async def cmd_allowlist(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Shows all allowed domains."""
    if message.chat.type == "private":
        return

    rules = await get_domain_rules(session, message.chat.id)
    allowed = [d for d, r in rules if r == "allow"]
    if not allowed:
        await message.reply("ℹ️ कोई विशेष डोमेन अनुमति सूची में नहीं है।")
        return

    await message.reply(
        "🌐 <b>स्वीकृत डोमेन (Allowlist):</b>\n\n"
        + "\n".join(f"• <code>{d}</code>" for d in allowed)
    )


async def inspect_links_in_message(
    message: Message, bot: Bot, session: AsyncSession
) -> bool:
    """
    Checks if a message contains unauthorized external links.
    Returns True if handled.
    """
    if not message.from_user or message.from_user.is_bot:
        return False

    if await is_user_admin(bot, message.chat.id, message.from_user.id):
        return False

    settings = await get_group_settings(session, message.chat.id)
    if not settings:
        return False

    _, domains = extract_domains_and_links(message)
    if not domains:
        return False

    rules = await get_domain_rules(session, message.chat.id)
    is_violating, offending_domain = check_link_violation(
        detected_domains=domains,
        domain_rules=rules,
        anti_link_enabled=settings.anti_link,
    )

    if not is_violating:
        return False

    await AnalyticsService.record_event(message.chat.id, "links_blocked_count", 1)
    await ModerationService.delete_message_safely(
        bot, message.chat.id, message.message_id
    )

    await ModerationService.warn_user(
        bot=bot,
        session=session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        reason=f"Unauthorized link: {offending_domain}",
        settings=settings,
    )

    return True
