import logging
from typing import Any

from aiogram import Bot

from app.config import get_settings
from app.database.repositories.moderation_repo import (
    record_audit_log,
    record_security_event,
)
from app.database.session import AsyncSessionLocal

settings = get_settings()
logger = logging.getLogger("tg_guard_pro.audit")


class AuditService:
    @staticmethod
    async def log_action(
        bot: Bot | None,
        chat_id: int,
        action: str,
        actor_id: int | None = None,
        target_id: int | None = None,
        details: dict[str, Any] | None = None,
        is_security_alert: bool = False,
    ) -> None:
        """
        Records an audit log entry in the database, and optionally forwards critical events to LOG_CHAT_ID.
        """
        async with AsyncSessionLocal() as session:
            await record_audit_log(
                session=session,
                chat_id=chat_id,
                actor_id=actor_id,
                target_id=target_id,
                action=action,
                details=details,
            )
            if is_security_alert:
                await record_security_event(
                    session=session,
                    chat_id=chat_id,
                    event_type=action,
                    severity="warning",
                    details=str(details) if details else None,
                )

        # Notify private log chat if configured
        if is_security_alert and bot and settings.log_chat_id != 0:
            try:
                alert_text = (
                    f"🚨 <b>SECURITY AUDIT ALERT</b>\n\n"
                    f"• <b>Action:</b> {action}\n"
                    f"• <b>Chat ID:</b> <code>{chat_id}</code>\n"
                    f"• <b>Actor:</b> <code>{actor_id or 'System'}</code>\n"
                    f"• <b>Target:</b> <code>{target_id or 'N/A'}</code>\n"
                    f"• <b>Details:</b> <code>{details or ''}</code>"
                )
                await bot.send_message(chat_id=settings.log_chat_id, text=alert_text)
            except Exception as e:
                logger.warning(
                    f"Failed to forward security audit log to LOG_CHAT_ID: {e}"
                )
