"""Repository for append-only workflow checkpoints."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WorkflowCheckpoint


async def create(
    session: AsyncSession,
    *,
    run_id: UUID,
    node: str,
    state: dict[str, Any],
) -> WorkflowCheckpoint:
    """Append the next checkpoint; callers never supply the step number."""
    latest = await get_latest(session, run_id)
    checkpoint = WorkflowCheckpoint(
        run_id=run_id,
        step=1 if latest is None else latest.step + 1,
        node=node,
        state=state,
    )
    session.add(checkpoint)
    await session.flush()
    await session.refresh(checkpoint)
    return checkpoint


async def get_latest(session: AsyncSession, run_id: UUID) -> WorkflowCheckpoint | None:
    result = await session.scalars(
        select(WorkflowCheckpoint)
        .where(WorkflowCheckpoint.run_id == run_id)
        .order_by(WorkflowCheckpoint.step.desc())
        .limit(1)
    )
    return result.one_or_none()


async def list_for_run(session: AsyncSession, run_id: UUID) -> Sequence[WorkflowCheckpoint]:
    result = await session.scalars(
        select(WorkflowCheckpoint)
        .where(WorkflowCheckpoint.run_id == run_id)
        .order_by(WorkflowCheckpoint.step.asc())
    )
    return result.all()
