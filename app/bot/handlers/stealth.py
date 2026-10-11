import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from app.config import get_settings
from app.core.permissions import is_master_owner
from app.services.stealth import StealthService

logger = logging.getLogger("tg_guard_pro.handlers.stealth")
router = Router(name="stealth")
settings = get_settings()


@router.edited_message()
async def on_message_edited(message: Message, bot: Bot) -> None:
    """Catches and reports edited messages in groups."""
    await StealthService.process_edited_message(bot, message)


@router.message(Command("say", "ghost"))
async def cmd_ghost_say(message: Message, bot: Bot) -> None:
    """
    Ghost Messenger:
    Allows Master Owner to send an anonymous message to any connected group from private chat.
    Usage: /say <chat_id> <text>
    """
    if not is_master_owner(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply(
            "⚠️ <b>उपयोग विधि:</b>\n<code>/say &lt;chat_id&gt; &lt;संदेश&gt;</code>\n\n"
            "उदाहरण:\n<code>/say -1001234567890 नमस्ते ग्रुप सदस्यों!</code>"
        )
        return

    try:
        target_chat_id = int(parts[1])
        ghost_text = parts[2]
    except ValueError:
        await message.reply("❌ अमान्य Chat ID! Chat ID एक संख्या होनी चाहिए (जैसे <code>-100...</code>)।")
        return

    success = await StealthService.send_ghost_message(bot, target_chat_id, ghost_text)
    if success:
        await message.reply(f"👻 <b>गुप्त संदेश सफलतापूर्वक पोस्ट किया गया!</b>\nग्रुप ID: <code>{target_chat_id}</code>")
    else:
        await message.reply("❌ संदेश भेजने में विफलता। कृपया सुनिश्चित करें कि बॉट उस ग्रुप में मौजूद है।")


@router.message(Command("nuke"))
async def cmd_emergency_nuke(message: Message, bot: Bot) -> None:
    """
    Emergency Panic Nuke:
    Puts the specified group into instant read-only lockdown.
    Usage: /nuke [chat_id]
    """
    if not is_master_owner(message.from_user.id):
        return

    target_chat_id = None
    parts = message.text.split()
    if len(parts) > 1 and (parts[1].startswith("-") or parts[1].isdigit()):
        target_chat_id = int(parts[1])
    elif message.chat.type != "private":
        target_chat_id = message.chat.id

    if not target_chat_id:
        await message.reply("⚠️ कृपया चैट ID प्रदान करें: <code>/nuke &lt;chat_id&gt;</code>")
        return

    success = await StealthService.execute_nuke(bot, target_chat_id)
    if success:
        await message.reply(
            f"🚨 <b>आपातकालीन लॉकडाउन सक्रिय (Nuke Executed)!</b>\n"
            f"ग्रुप <code>{target_chat_id}</code> को केवल-पठन (Read-Only) मोड में लॉक कर दिया गया है।\n\n"
            f"अनलॉक करने के लिए: <code>/unnuke {target_chat_id}</code> चलाएं।"
        )
    else:
        await message.reply("❌ लॉकडाउन सक्रिय करने में विफलता।")


@router.message(Command("unnuke", "unlockgroup"))
async def cmd_unnuke(message: Message, bot: Bot) -> None:
    """
    Unlocks group from read-only emergency lockdown.
    Usage: /unnuke [chat_id]
    """
    if not is_master_owner(message.from_user.id):
        return

    target_chat_id = None
    parts = message.text.split()
    if len(parts) > 1 and (parts[1].startswith("-") or parts[1].isdigit()):
        target_chat_id = int(parts[1])
    elif message.chat.type != "private":
        target_chat_id = message.chat.id

    if not target_chat_id:
        await message.reply("⚠️ कृपया चैट ID प्रदान करें: <code>/unnuke &lt;chat_id&gt;</code>")
        return

    try:
        normal_perms = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
        )
        await bot.set_chat_permissions(chat_id=target_chat_id, permissions=normal_perms)
        await bot.send_message(
            chat_id=target_chat_id,
            text="🟢 <b>ग्रुप सामान्य मोड में बहाल (Lockdown Lifted)!</b>\nसभी सदस्य अब संदेश भेज सकते हैं।"
        )
        await message.reply(f"✅ ग्रुप <code>{target_chat_id}</code> को सामान्य मोड में बहाल कर दिया गया है।")
    except Exception as e:
        await message.reply(f"❌ अनलॉक करने में त्रुटि: {e}")


@router.message(Command("claimmaster"))
async def cmd_claim_master(message: Message) -> None:
    """
    Dead Man's Switch:
    Recovers Master Ownership onto a new Telegram account using the recovery token.
    Usage: /claimmaster <token>
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("⚠️ कृपया सीक्रेट रिकवरी टोकन प्रदान करें:\n<code>/claimmaster &lt;recovery_key&gt;</code>")
        return

    token = parts[1].strip()
    recovered = StealthService.claim_master_account(message.from_user.id, token)

    if recovered:
        await message.reply(
            f"👑 <b>सर्वोच्च मास्टर ओनरशिप बहाल (Master Account Recovered)!</b>\n\n"
            f"नया Master Owner ID: <code>{message.from_user.id}</code>\n"
            f"सभी ग्रुप्स और कंट्रोल डैशबोर्ड्स का सर्वोच्च अधिकार आपके इस नए खाते पर स्थानांतरित कर दिया गया है।\n\n"
            f"प्राइवेट में <code>/master</code> चलाकर डैशबोर्ड खोलें।"
        )
    else:
        await message.reply("❌ <b>अमान्य रिकवरी टोकन (Invalid Secret Token)!</b> पहुंच अस्वीकृत।")
