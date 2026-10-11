import time
import logging
from typing import Optional, Dict, Any
from aiogram import Bot
from app.config import get_settings
from app.database.session import AsyncSessionLocal
from app.database.repositories.moderation_repo import record_security_event

settings = get_settings()
logger = logging.getLogger("tg_guard_pro.alerts")

# Deduplication cache: alert_key -> timestamp
_ALERT_DEDUP_CACHE: Dict[str, float] = {}
DEDUP_WINDOW_SECONDS = 60.0

ALERT_PRIORITY_ICONS = {
    "CRITICAL": "🚨 [CRITICAL]",
    "HIGH": "⚠️ [HIGH]",
    "MEDIUM": "ℹ️ [MEDIUM]",
    "LOW": "📝 [LOW]",
}


class AlertService:
    @staticmethod
    def _is_duplicate(key: str) -> bool:
        now = time.time()
        last_time = _ALERT_DEDUP_CACHE.get(key, 0.0)
        if now - last_time < DEDUP_WINDOW_SECONDS:
            return True
        _ALERT_DEDUP_CACHE[key] = now
        # Periodic cleanup of old entries
        if len(_ALERT_DEDUP_CACHE) > 1000:
            cutoff = now - 3600
            stale = [k for k, v in _ALERT_DEDUP_CACHE.items() if v < cutoff]
            for k in stale:
                _ALERT_DEDUP_CACHE.pop(k, None)
        return False

    @classmethod
    async def dispatch_alert(
        cls,
        bot: Bot,
        title: str,
        message: str,
        priority: str = "MEDIUM",
        chat_id: Optional[int] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """
        Dispatches a structured alert to LOG_CHAT_ID with priority badge and deduplication.
        """
        priority = priority.upper()
        if priority not in ALERT_PRIORITY_ICONS:
            priority = "MEDIUM"

        key = dedup_key or f"{title}:{chat_id}:{priority}"
        if cls._is_duplicate(key):
            logger.debug(f"Suppressed duplicate alert: {key}")
            return False

        # Record in database security events
        if chat_id:
            try:
                async with AsyncSessionLocal() as session:
                    await record_security_event(
                        session=session,
                        chat_id=chat_id,
                        event_type=title,
                        severity=priority.lower(),
                        details=message,
                    )
            except Exception as e:
                logger.warning(f"Failed to record security event in db: {e}")

        # Send to LOG_CHAT_ID
        target_chat = settings.log_chat_id
        if not target_chat or target_chat == 0:
            return False

        badge = ALERT_PRIORITY_ICONS.get(priority, "ℹ️")
        chat_info = f"• <b>चैट/ग्रुप:</b> <code>{chat_id}</code>\n" if chat_id else ""

        alert_text = (
            f"{badge} <b>{title}</b>\n\n"
            f"{chat_info}"
            f"{message}\n\n"
            f"<i>TG GUARD PRO V4 Live Alert</i>"
        )

        try:
            await bot.send_message(chat_id=target_chat, text=alert_text)
            return True
        except Exception as e:
            logger.warning(f"Could not deliver alert to log chat {target_chat}: {e}")
            return False
