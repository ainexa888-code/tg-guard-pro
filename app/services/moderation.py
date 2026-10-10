from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.types import ChatPermissions
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import GroupSettings
from app.database.repositories.moderation_repo import (
    add_warning,
    record_audit_log,
    record_moderation_action,
    reset_warnings,
)


class ModerationService:
    @staticmethod
    async def delete_message_safely(bot: Bot, chat_id: int, message_id: int) -> bool:
        """Attempts to delete a message, handling lack of permissions or deleted message gracefully."""
        try:
            return await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            return False

    @classmethod
    async def warn_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        reason: str,
        admin_id: int | None = None,
        settings: GroupSettings | None = None,
    ) -> tuple[int, str | None]:
        """
        Issues a warning to a user, checking escalation against warn_limit.
        Returns (current_warnings_count, escalation_action_taken).
        """
        warn_count = await add_warning(session, chat_id, user_id, reason, admin_id)
        await record_moderation_action(
            session=session,
            chat_id=chat_id,
            user_id=user_id,
            action="warn",
            reason=reason,
            admin_id=admin_id,
        )
        await record_audit_log(
            session=session,
            chat_id=chat_id,
            actor_id=admin_id,
            target_id=user_id,
            action="user_warned",
            details={"warnings": warn_count, "reason": reason},
        )

        warn_limit = settings.warn_limit if settings else 3
        escalation_action = None

        if warn_count >= warn_limit:
            action_type = settings.warn_action if settings else "mute"
            escalation_action = action_type
            if action_type == "ban":
                await cls.ban_user(
                    bot,
                    session,
                    chat_id,
                    user_id,
                    reason="Exceeded warning limit",
                    admin_id=admin_id,
                )
            elif action_type == "kick":
                await cls.kick_user(
                    bot,
                    session,
                    chat_id,
                    user_id,
                    reason="Exceeded warning limit",
                    admin_id=admin_id,
                )
            else:  # default to mute
                await cls.mute_user(
                    bot,
                    session,
                    chat_id,
                    user_id,
                    duration_seconds=86400,
                    reason="Exceeded warning limit",
                    admin_id=admin_id,
                )
            # Reset warnings after escalation action is applied
            await reset_warnings(session, chat_id, user_id)

        return warn_count, escalation_action

    @classmethod
    async def mute_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        duration_seconds: int | None = 3600,
        reason: str | None = None,
        admin_id: int | None = None,
    ) -> bool:
        """Restricts a user from speaking for duration_seconds (or indefinitely if None)."""
        until_date = None
        if duration_seconds:
            until_date = datetime.now(UTC) + timedelta(seconds=duration_seconds)

        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
                until_date=until_date,
            )
            await record_moderation_action(
                session=session,
                chat_id=chat_id,
                user_id=user_id,
                action="mute",
                reason=reason,
                admin_id=admin_id,
                duration_seconds=duration_seconds,
            )
            await record_audit_log(
                session=session,
                chat_id=chat_id,
                actor_id=admin_id,
                target_id=user_id,
                action="user_muted",
                details={"duration": duration_seconds, "reason": reason},
            )
            return True
        except Exception:
            return False

    @classmethod
    async def unmute_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        admin_id: int | None = None,
    ) -> bool:
        """Restores a user's messaging permissions."""
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            await record_moderation_action(
                session=session,
                chat_id=chat_id,
                user_id=user_id,
                action="unmute",
                admin_id=admin_id,
            )
            await record_audit_log(
                session=session,
                chat_id=chat_id,
                actor_id=admin_id,
                target_id=user_id,
                action="user_unmuted",
            )
            return True
        except Exception:
            return False

    @classmethod
    async def ban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        reason: str | None = None,
        admin_id: int | None = None,
    ) -> bool:
        """Bans a user from the chat."""
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await record_moderation_action(
                session=session,
                chat_id=chat_id,
                user_id=user_id,
                action="ban",
                reason=reason,
                admin_id=admin_id,
            )
            await record_audit_log(
                session=session,
                chat_id=chat_id,
                actor_id=admin_id,
                target_id=user_id,
                action="user_banned",
                details={"reason": reason},
            )
            return True
        except Exception:
            return False

    @classmethod
    async def unban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        admin_id: int | None = None,
    ) -> bool:
        """Unbans a user from the chat."""
        try:
            await bot.unban_chat_member(
                chat_id=chat_id, user_id=user_id, only_if_banned=True
            )
            await record_moderation_action(
                session=session,
                chat_id=chat_id,
                user_id=user_id,
                action="unban",
                admin_id=admin_id,
            )
            await record_audit_log(
                session=session,
                chat_id=chat_id,
                actor_id=admin_id,
                target_id=user_id,
                action="user_unbanned",
            )
            return True
        except Exception:
            return False

    @classmethod
    async def kick_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        reason: str | None = None,
        admin_id: int | None = None,
    ) -> bool:
        """Kicks a user (ban followed immediately by unban so they can rejoin if invited)."""
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.unban_chat_member(
                chat_id=chat_id, user_id=user_id, only_if_banned=True
            )
            await record_moderation_action(
                session=session,
                chat_id=chat_id,
                user_id=user_id,
                action="kick",
                reason=reason,
                admin_id=admin_id,
            )
            await record_audit_log(
                session=session,
                chat_id=chat_id,
                actor_id=admin_id,
                target_id=user_id,
                action="user_kicked",
                details={"reason": reason},
            )
            return True
        except Exception:
            return False
