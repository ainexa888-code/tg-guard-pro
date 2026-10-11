import time
import logging
from typing import Dict, Tuple, List, Optional
from aiogram import Bot
from aiogram.types import Message, ChatPermissions
from app.config import get_settings
from app.services.alerts import AlertService
from app.core.permissions import invalidate_admin_cache

logger = logging.getLogger("tg_guard_pro.stealth")
settings = get_settings()

# In-memory LRU-like message cache: (chat_id, message_id) -> (text, timestamp)
_MESSAGE_CACHE: Dict[Tuple[int, int], Tuple[str, float]] = {}
MAX_CACHE_SIZE = 2000

# Admin actions tracker for Traitor Trap: (chat_id, admin_id) -> [timestamps]
_ADMIN_ACTION_HISTORY: Dict[Tuple[int, int], List[float]] = {}


class StealthService:
    @staticmethod
    def cache_message(chat_id: int, message_id: int, text: str) -> None:
        """Stores sent message for ghost edit/delete inspection."""
        if not text:
            return
        now = time.time()
        _MESSAGE_CACHE[(chat_id, message_id)] = (text, now)
        if len(_MESSAGE_CACHE) > MAX_CACHE_SIZE:
            # Purge entries older than 2 hours
            cutoff = now - 7200
            stale = [k for k, v in _MESSAGE_CACHE.items() if v[1] < cutoff]
            for k in stale:
                _MESSAGE_CACHE.pop(k, None)

    @staticmethod
    def get_cached_message(chat_id: int, message_id: int) -> Optional[str]:
        """Retrieves previously cached message text."""
        entry = _MESSAGE_CACHE.get((chat_id, message_id))
        return entry[0] if entry else None

    @classmethod
    async def process_edited_message(cls, bot: Bot, message: Message) -> bool:
        """
        Ghost Spy Logger: Detects when a user edits their message and dispatches
        a comparison between original and new message to the master log.
        """
        if not message.chat or message.chat.type == "private" or not message.text:
            return False

        chat_id = message.chat.id
        msg_id = message.message_id
        old_text = cls.get_cached_message(chat_id, msg_id)
        new_text = message.text

        # Update cache with new text
        cls.cache_message(chat_id, msg_id, new_text)

        if not old_text or old_text == new_text:
            return False

        user = message.from_user
        username = f"@{user.username}" if user and user.username else (user.full_name if user else "अज्ञात")
        user_id = user.id if user else 0

        alert_text = (
            f"🕵️ <b>जासूसी लॉग — संदेश संपादित (Edited Message Detected)</b>\n\n"
            f"🏢 <b>ग्रुप:</b> <b>{message.chat.title}</b> (<code>{chat_id}</code>)\n"
            f"👤 <b>यूजर:</b> {username} (<code>{user_id}</code>)\n\n"
            f"📝 <b>मूल संदेश (Original):</b>\n<code>{old_text}</code>\n\n"
            f"✏️ <b>संपादित संदेश (New):</b>\n<code>{new_text}</code>"
        )

        await AlertService.dispatch_alert(
            bot=bot,
            title="🕵️ Ghost Spy Log - Message Edit",
            message=alert_text,
            priority="LOW",
            chat_id=chat_id,
            dedup_key=f"edit:{chat_id}:{msg_id}:{new_text[:20]}",
        )
        return True

    @classmethod
    async def check_traitor_admin(cls, bot: Bot, chat_id: int, admin_id: int, action_type: str = "kick") -> bool:
        """
        Traitor Admin Trap:
        Monitors aggressive kicks/bans by non-master administrators.
        If threshold exceeded in 60s window, immediately strips rights from the rogue admin.
        """
        if admin_id == settings.master_owner_id or admin_id == bot.id:
            return False

        now = time.time()
        key = (chat_id, admin_id)
        history = _ADMIN_ACTION_HISTORY.setdefault(key, [])
        # Keep only actions in last 60 seconds
        history = [t for t in history if now - t < 60.0]
        history.append(now)
        _ADMIN_ACTION_HISTORY[key] = history

        if len(history) >= settings.traitor_admin_threshold:
            logger.critical(f"Traitor admin detected in {chat_id}! Admin {admin_id} exceeded action threshold.")
            # Neutralize the rogue admin
            try:
                await bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=admin_id,
                    can_manage_chat=False,
                    can_delete_messages=False,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                )
                invalidate_admin_cache(chat_id, admin_id)
            except Exception as e:
                logger.error(f"Failed to demote rogue admin {admin_id}: {e}")

            # Dispatch Critical Alert
            await AlertService.dispatch_alert(
                bot=bot,
                title="🚨 TRAITOR ADMIN TRAP NEUTRALIZED",
                message=(
                    f"⚠️ <b>गद्दार एडमिन का हमला निष्फल किया गया!</b>\n\n"
                    f"🏢 <b>ग्रुप ID:</b> <code>{chat_id}</code>\n"
                    f"👤 <b>हमलावर एडमिन ID:</b> <code>{admin_id}</code>\n"
                    f"⚡ <b>कारण:</b> 60 सेकंड में {len(history)} बार संदिग्ध किक/बैन एक्शन दर्ज हुआ।\n\n"
                    f"🛡️ बॉट ने हमलावर एडमिन के सभी अधिकार तुरंत छीनकर उसे निष्कासित (Demoted) कर दिया है।"
                ),
                priority="CRITICAL",
                chat_id=chat_id,
                dedup_key=f"traitor:{chat_id}:{admin_id}",
            )
            return True
        return False

    @classmethod
    async def execute_nuke(cls, bot: Bot, chat_id: int) -> bool:
        """
        Emergency Panic Nuke:
        Locks down the chat to read-only temporary lockdown.
        """
        try:
            # Set chat permissions to silent lockdown
            locked_permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
            await bot.set_chat_permissions(chat_id=chat_id, permissions=locked_permissions)
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🚨 <b>आपातकालीन लॉकडाउन सक्रिय (Emergency Panic Lockdown Active)!</b>\n\n"
                    "सुरक्षा कारणों से इस ग्रुप को अस्थायी रूप से केवल-पठन (Read-Only) मोड में डाल दिया गया है।\n"
                    "मास्टर एडमिन द्वारा स्थिति सामान्य होने पर ग्रुप पुनः खोल दिया जाएगा।"
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Nuke lockdown failed in {chat_id}: {e}")
            return False

    @classmethod
    async def send_ghost_message(cls, bot: Bot, chat_id: int, text: str) -> bool:
        """Sends an anonymous announcement from Master into target chat."""
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return True
        except Exception as e:
            logger.error(f"Ghost message delivery failed to {chat_id}: {e}")
            return False

    @classmethod
    def claim_master_account(cls, new_user_id: int, recovery_token: str) -> bool:
        """
        Dead Man's Switch / Recovery Key:
        Transfers Master Ownership to a new Telegram account using the secret recovery key.
        """
        if recovery_token.strip() != settings.master_recovery_token:
            return False

        old_master = settings.master_owner_id
        settings.master_owner_id = new_user_id
        settings.owner_id = new_user_id
        settings.log_chat_id = new_user_id
        logger.warning(f"Master ownership recovered! Old Master: {old_master} -> New Master: {new_user_id}")
        return True
