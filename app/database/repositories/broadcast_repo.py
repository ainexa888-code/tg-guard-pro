from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    BroadcastCampaign,
    BroadcastDelivery,
    Group,
    GroupSettings,
)


async def get_opted_in_groups(session: AsyncSession) -> list[int]:
    """Retrieves all active group chat IDs that have permitted broadcast announcements."""
    stmt = (
        select(Group.id)
        .join(GroupSettings, Group.id == GroupSettings.group_id)
        .where(
            Group.is_active == True,
            GroupSettings.broadcast_optin == True,
        )
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def create_campaign(
    session: AsyncSession,
    campaign_id: str,
    creator_id: int,
    text: str,
    total_groups: int,
) -> BroadcastCampaign:
    campaign = BroadcastCampaign(
        id=campaign_id,
        creator_id=creator_id,
        message_text=text,
        total_groups=total_groups,
        status="sending",
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def record_delivery(
    session: AsyncSession,
    campaign_id: str,
    group_id: int,
    status: str,
    error_message: str | None = None,
) -> BroadcastDelivery:
    delivery = BroadcastDelivery(
        campaign_id=campaign_id,
        group_id=group_id,
        status=status,
        error_message=error_message,
        sent_at=datetime.now(UTC) if status == "sent" else None,
    )
    session.add(delivery)
    await session.commit()
    return delivery


async def complete_campaign(
    session: AsyncSession,
    campaign_id: str,
    successful_groups: int,
    failed_groups: int,
) -> BroadcastCampaign | None:
    stmt = select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id)
    res = await session.execute(stmt)
    campaign = res.scalar_one_or_none()
    if campaign:
        campaign.successful_groups = successful_groups
        campaign.failed_groups = failed_groups
        campaign.status = "completed"
        campaign.completed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(campaign)
    return campaign
