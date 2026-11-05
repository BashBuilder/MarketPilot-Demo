"""Campaign creation, listing and summary endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RunLauncher, get_run_launcher, get_session
from app.api.schemas import CampaignCreated, CampaignSummary, CreateCampaignRequest
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ValidationFailure
from app.database.models import Campaign
from app.database.repositories import campaigns, runs, versions

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignCreated, status_code=201)
async def create_campaign(
    payload: CreateCampaignRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    launcher: Annotated[RunLauncher, Depends(get_run_launcher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CampaignCreated:
    """Create the campaign and its first run, then launch the run."""
    idea = _validated_idea(payload.idea, settings.max_idea_length)
    campaign = await campaigns.create(session, idea=idea)
    run = await runs.create(session, campaign_id=campaign.id)
    # Commit before launching so the runner can read the row immediately.
    await session.commit()
    await launcher.start(run.id)
    return CampaignCreated(campaign_id=campaign.id, run_id=run.id)


@router.get("", response_model=list[CampaignSummary])
async def list_campaigns(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CampaignSummary]:
    """Return newest campaigns first with their latest version and active run."""
    rows = await campaigns.list_all(session)
    return [await _summary(session, campaign) for campaign in rows]


@router.get("/{campaign_id}", response_model=CampaignSummary)
async def get_campaign(
    campaign_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignSummary:
    """Return one campaign summary or a 404 error envelope."""
    campaign = await campaigns.get(session, campaign_id)
    if campaign is None:
        raise NotFoundError(
            f"campaign not found: {campaign_id}",
            details={"id": str(campaign_id)},
        )
    return await _summary(session, campaign)


def _validated_idea(value: str, max_length: int) -> str:
    idea = value.strip()
    if not idea:
        raise ValidationFailure("idea must not be blank")
    if len(idea) > max_length:
        raise ValidationFailure(
            f"idea must be at most {max_length} characters",
            details={"max_length": max_length, "length": len(idea)},
        )
    return idea


async def _summary(session: AsyncSession, campaign: Campaign) -> CampaignSummary:
    latest = await versions.get_latest(session, campaign.id)
    active = await runs.get_active(session, campaign.id)
    return CampaignSummary(
        id=campaign.id,
        idea=campaign.idea,
        status=campaign.status,
        latest_version=latest.version if latest is not None else None,
        latest_score=latest.score if latest is not None else None,
        active_run_id=active.id if active is not None else None,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )
