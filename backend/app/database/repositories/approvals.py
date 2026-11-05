"""Repository functions for human approvals."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Approval, ApprovalDecision


async def create(
    session: AsyncSession,
    *,
    run_id: UUID,
    campaign_version_id: UUID,
    decision: ApprovalDecision,
    comment: str | None = None,
    target_node: str | None = None,
) -> Approval:
    """Record an approve or revise action; rows are never updated."""
    approval = Approval(
        run_id=run_id,
        campaign_version_id=campaign_version_id,
        decision=decision,
        comment=comment,
        target_node=target_node,
    )
    session.add(approval)
    await session.flush()
    await session.refresh(approval)
    return approval


async def list_for_run(session: AsyncSession, run_id: UUID) -> Sequence[Approval]:
    result = await session.scalars(
        select(Approval).where(Approval.run_id == run_id).order_by(Approval.created_at.asc())
    )
    return result.all()


async def get_latest_for_run(session: AsyncSession, run_id: UUID) -> Approval | None:
    result = await session.scalars(
        select(Approval)
        .where(Approval.run_id == run_id)
        .order_by(Approval.created_at.desc())
        .limit(1)
    )
    return result.one_or_none()
