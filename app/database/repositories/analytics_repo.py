from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import GroupDailyStat


async def increment_daily_stat(
    session: AsyncSession,
    chat_id: int,
    field_name: str,
    amount: int = 1,
) -> None:
    """Safely increments a specific counter in the group daily stats."""
    today = date.today()
    stmt = select(GroupDailyStat).where(
        GroupDailyStat.group_id == chat_id,
        GroupDailyStat.stat_date == today,
    )
    res = await session.execute(stmt)
    stat = res.scalar_one_or_none()

    if not stat:
        stat = GroupDailyStat(group_id=chat_id, stat_date=today)
        if hasattr(stat, field_name):
            setattr(stat, field_name, amount)
        session.add(stat)
    else:
        if hasattr(stat, field_name):
            current = getattr(stat, field_name) or 0
            setattr(stat, field_name, current + amount)

    await session.commit()


async def get_stats_summary(
    session: AsyncSession,
    chat_id: int,
    days: int = 7,
) -> dict[str, Any]:
    """Retrieves aggregated statistics for the past N days."""
    cutoff = date.today() - timedelta(days=days)
    stmt = select(
        func.sum(GroupDailyStat.messages_count).label("total_messages"),
        func.sum(GroupDailyStat.joins_count).label("total_joins"),
        func.sum(GroupDailyStat.leaves_count).label("total_leaves"),
        func.sum(GroupDailyStat.spam_blocked_count).label("spam_blocked"),
        func.sum(GroupDailyStat.links_blocked_count).label("links_blocked"),
        func.sum(GroupDailyStat.fonts_blocked_count).label("fonts_blocked"),
        func.sum(GroupDailyStat.badwords_blocked_count).label("badwords_blocked"),
        func.sum(GroupDailyStat.captcha_success_count).label("captcha_success"),
        func.sum(GroupDailyStat.captcha_failed_count).label("captcha_failed"),
        func.sum(GroupDailyStat.reactions_count).label("reactions_count"),
    ).where(
        GroupDailyStat.group_id == chat_id,
        GroupDailyStat.stat_date >= cutoff,
    )

    res = await session.execute(stmt)
    row = res.one_or_none()

    if not row:
        return {
            "days": days,
            "total_messages": 0,
            "total_joins": 0,
            "total_leaves": 0,
            "spam_blocked": 0,
            "links_blocked": 0,
            "fonts_blocked": 0,
            "badwords_blocked": 0,
            "captcha_success": 0,
            "captcha_failed": 0,
            "reactions_count": 0,
        }

    return {
        "days": days,
        "total_messages": row.total_messages or 0,
        "total_joins": row.total_joins or 0,
        "total_leaves": row.total_leaves or 0,
        "spam_blocked": row.spam_blocked or 0,
        "links_blocked": row.links_blocked or 0,
        "fonts_blocked": row.fonts_blocked or 0,
        "badwords_blocked": row.badwords_blocked or 0,
        "captcha_success": row.captcha_success or 0,
        "captcha_failed": row.captcha_failed or 0,
        "reactions_count": row.reactions_count or 0,
    }
