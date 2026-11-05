"""Repository functions for workflow runs."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import RunStatus, WorkflowRun


async def create(session: AsyncSession, *, campaign_id: UUID) -> WorkflowRun:
    """Insert a pending run for a campaign."""
    run = WorkflowRun(campaign_id=campaign_id)
    session.add(run)
    await session.flush()
    await session.refresh(run)
    return run


async def get(session: AsyncSession, run_id: UUID) -> WorkflowRun | None:
    return await session.get(WorkflowRun, run_id)


async def list_for_campaign(session: AsyncSession, campaign_id: UUID) -> Sequence[WorkflowRun]:
    """Return a campaign's runs, oldest first so the UI reads chronologically."""
    result = await session.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.campaign_id == campaign_id)
        .order_by(WorkflowRun.created_at.asc())
    )
    return result.all()


async def get_active(session: AsyncSession, campaign_id: UUID) -> WorkflowRun | None:
    """Return the newest run that has not reached a terminal status."""
    result = await session.scalars(
        select(WorkflowRun)
        .where(
            WorkflowRun.campaign_id == campaign_id,
            WorkflowRun.status.not_in((RunStatus.COMPLETED, RunStatus.FAILED)),
        )
        .order_by(WorkflowRun.created_at.desc())
        .limit(1)
    )
    return result.one_or_none()


async def set_status(
    session: AsyncSession,
    run_id: UUID,
    status: RunStatus,
    *,
    current_node: str | None = None,
    error: str | None = None,
) -> WorkflowRun | None:
    """Advance a run; passing no node or error clears both fields."""
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        return None
    run.status = status
    run.current_node = current_node
    run.error = error
    await session.flush()
    await session.refresh(run)
    return run
