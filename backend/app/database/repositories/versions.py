"""Repository functions for append-only campaign versions."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CampaignVersion


async def create(
    session: AsyncSession,
    *,
    campaign_id: UUID,
    package: dict[str, Any],
    parent_version_id: UUID | None = None,
    score: float | None = None,
) -> CampaignVersion:
    """Append the next version; callers never supply the version number."""
    latest = await get_latest(session, campaign_id)
    version = CampaignVersion(
        campaign_id=campaign_id,
        version=1 if latest is None else latest.version + 1,
        parent_version_id=parent_version_id,
        package=package,
        score=score,
    )
    session.add(version)
    await session.flush()
    await session.refresh(version)
    return version


async def get(
    session: AsyncSession, campaign_id: UUID, version_number: int
) -> CampaignVersion | None:
    result = await session.scalars(
        select(CampaignVersion).where(
            CampaignVersion.campaign_id == campaign_id,
            CampaignVersion.version == version_number,
        )
    )
    return result.one_or_none()


async def get_latest(session: AsyncSession, campaign_id: UUID) -> CampaignVersion | None:
    result = await session.scalars(
        select(CampaignVersion)
        .where(CampaignVersion.campaign_id == campaign_id)
        .order_by(CampaignVersion.version.desc())
        .limit(1)
    )
    return result.one_or_none()


async def list_for_campaign(session: AsyncSession, campaign_id: UUID) -> Sequence[CampaignVersion]:
    result = await session.scalars(
        select(CampaignVersion)
        .where(CampaignVersion.campaign_id == campaign_id)
        .order_by(CampaignVersion.version.asc())
    )
    return result.all()
