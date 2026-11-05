"""Version history, package detail and diff endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.api.schemas import CampaignPackage, VersionDiff, VersionSummary
from app.core.errors import NotFoundError
from app.database.models import Campaign, CampaignVersion
from app.database.repositories import campaigns, versions
from app.graph.diff import compute_diff

router = APIRouter(prefix="/campaigns/{campaign_id}/versions", tags=["versions"])


@router.get("", response_model=list[VersionSummary])
async def list_versions(
    campaign_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[VersionSummary]:
    """Return a campaign's append-only version history, oldest first."""
    await _require_campaign(session, campaign_id)
    rows = await versions.list_for_campaign(session, campaign_id)
    return [VersionSummary.model_validate(row) for row in rows]


@router.get("/{from_version}/diff/{to_version}", response_model=VersionDiff)
async def diff_versions(
    campaign_id: UUID,
    from_version: int,
    to_version: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionDiff:
    """Return the leaf fields that differ between two package snapshots."""
    await _require_campaign(session, campaign_id)
    before = await _require_version(session, campaign_id, from_version)
    after = await _require_version(session, campaign_id, to_version)
    return VersionDiff.model_validate(compute_diff(before, after))


@router.get(
    "/{version_number}",
    response_model=CampaignPackage,
    response_model_exclude_none=True,
)
async def get_version(
    campaign_id: UUID,
    version_number: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignPackage:
    """Return one version's full package snapshot."""
    await _require_campaign(session, campaign_id)
    row = await _require_version(session, campaign_id, version_number)
    return CampaignPackage.model_validate(row.package)


async def _require_campaign(session: AsyncSession, campaign_id: UUID) -> Campaign:
    campaign = await campaigns.get(session, campaign_id)
    if campaign is None:
        raise NotFoundError(
            f"campaign not found: {campaign_id}",
            details={"id": str(campaign_id)},
        )
    return campaign


async def _require_version(
    session: AsyncSession, campaign_id: UUID, version: int
) -> CampaignVersion:
    row = await versions.get(session, campaign_id, version)
    if row is None:
        raise NotFoundError(
            f"campaign version not found: {campaign_id} version {version}",
            details={"campaign_id": str(campaign_id), "version": version},
        )
    return row
