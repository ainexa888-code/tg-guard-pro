import json
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AuditLog,
    CaptchaChallenge,
    MemberWarning,
    ModerationAction,
    ScheduledDeletion,
    SecurityEvent,
)


async def add_warning(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    reason: str,
    warned_by: int | None = None,
) -> int:
    """Adds a warning for a user and returns total warning count."""
    warn = MemberWarning(
        group_id=chat_id,
        user_id=user_id,
        reason=reason,
        warned_by=warned_by,
    )
    session.add(warn)
    await session.commit()

    count_stmt = select(func.count(MemberWarning.id)).where(
        MemberWarning.group_id == chat_id,
        MemberWarning.user_id == user_id,
    )
    res = await session.execute(count_stmt)
    return res.scalar_one() or 1


async def get_warnings_count(session: AsyncSession, chat_id: int, user_id: int) -> int:
    stmt = select(func.count(MemberWarning.id)).where(
        MemberWarning.group_id == chat_id,
        MemberWarning.user_id == user_id,
    )
    res = await session.execute(stmt)
    return res.scalar_one() or 0


async def reset_warnings(session: AsyncSession, chat_id: int, user_id: int) -> int:
    stmt = delete(MemberWarning).where(
        MemberWarning.group_id == chat_id,
        MemberWarning.user_id == user_id,
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount


async def record_moderation_action(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    action: str,
    reason: str | None = None,
    admin_id: int | None = None,
    duration_seconds: int | None = None,
) -> ModerationAction:
    entry = ModerationAction(
        group_id=chat_id,
        user_id=user_id,
        action=action,
        reason=reason,
        admin_id=admin_id,
        duration_seconds=duration_seconds,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def record_audit_log(
    session: AsyncSession,
    chat_id: int,
    actor_id: int | None,
    target_id: int | None,
    action: str,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        group_id=chat_id,
        actor_id=actor_id,
        target_id=target_id,
        action=action,
        details=json.dumps(details) if details else None,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_audit_logs(
    session: AsyncSession,
    chat_id: int,
    limit: int = 15,
    offset: int = 0,
) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.group_id == chat_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def record_security_event(
    session: AsyncSession,
    chat_id: int,
    event_type: str,
    severity: str = "warning",
    details: str | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        group_id=chat_id,
        event_type=event_type,
        severity=severity,
        details=details,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


# Captcha repository functions
async def create_captcha_challenge(
    session: AsyncSession,
    challenge_id: str,
    chat_id: int,
    user_id: int,
    challenge_type: str,
    answer: str,
    expires_at: datetime,
    message_id: int | None = None,
) -> CaptchaChallenge:
    challenge = CaptchaChallenge(
        id=challenge_id,
        group_id=chat_id,
        user_id=user_id,
        challenge_type=challenge_type,
        answer=answer,
        expires_at=expires_at,
        message_id=message_id,
    )
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return challenge


async def get_captcha_challenge(
    session: AsyncSession, challenge_id: str
) -> CaptchaChallenge | None:
    stmt = select(CaptchaChallenge).where(CaptchaChallenge.id == challenge_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def mark_captcha_solved(session: AsyncSession, challenge_id: str) -> bool:
    stmt = select(CaptchaChallenge).where(CaptchaChallenge.id == challenge_id)
    res = await session.execute(stmt)
    challenge = res.scalar_one_or_none()
    if challenge:
        challenge.is_solved = True
        await session.commit()
        return True
    return False


async def delete_captcha_challenge(session: AsyncSession, challenge_id: str) -> bool:
    stmt = delete(CaptchaChallenge).where(CaptchaChallenge.id == challenge_id)
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0


# Scheduled deletion repository functions
async def schedule_message_deletion(
    session: AsyncSession,
    chat_id: int,
    message_id: int,
    delete_at: datetime,
    reason: str | None = None,
) -> ScheduledDeletion:
    entry = ScheduledDeletion(
        group_id=chat_id,
        message_id=message_id,
        delete_at=delete_at,
        reason=reason,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_due_message_deletions(session: AsyncSession) -> list[ScheduledDeletion]:
    now = datetime.now(UTC)
    stmt = select(ScheduledDeletion).where(
        ScheduledDeletion.is_processed == False,
        ScheduledDeletion.delete_at <= now,
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def mark_deletion_processed(session: AsyncSession, deletion_id: int) -> None:
    stmt = select(ScheduledDeletion).where(ScheduledDeletion.id == deletion_id)
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if item:
        item.is_processed = True
        await session.commit()
