"""Repository functions for campaigns."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Campaign, CampaignStatus


async def create(session: AsyncSession, *, idea: str) -> Campaign:
    """Insert a draft campaign and return it with server defaults populated."""
    campaign = Campaign(idea=idea)
    session.add(campaign)
    await session.flush()
    await session.refresh(campaign)
    return campaign


async def get(session: AsyncSession, campaign_id: UUID) -> Campaign | None:
    return await session.get(Campaign, campaign_id)


async def list_all(
    session: AsyncSession, *, limit: int = 50, offset: int = 0
) -> Sequence[Campaign]:
    """Return newest campaigns first, bounded so a request cannot scan the table."""
    result = await session.scalars(
        select(Campaign).order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
    )
    return result.all()


async def set_status(
    session: AsyncSession, campaign_id: UUID, status: CampaignStatus
) -> Campaign | None:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        return None
    campaign.status = status
    await session.flush()
    await session.refresh(campaign)
    return campaign
