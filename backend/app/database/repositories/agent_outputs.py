"""Repository for immutable agent output rows."""

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AgentOutput


async def create(
    session: AsyncSession,
    *,
    run_id: UUID,
    agent: str,
    output: Mapping[str, Any],
) -> AgentOutput:
    """Append one validated output; callers own the transaction that commits it."""
    row = AgentOutput(run_id=run_id, agent=agent, output=dict(output))
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def list_for_run(session: AsyncSession, run_id: UUID) -> Sequence[AgentOutput]:
    """Return a run's handoffs oldest first so replay matches execution order."""
    result = await session.scalars(
        select(AgentOutput)
        .where(AgentOutput.run_id == run_id)
        .order_by(AgentOutput.created_at.asc())
    )
    return result.all()
