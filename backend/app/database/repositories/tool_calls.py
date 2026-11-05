"""Repository for immutable tool-call audit rows."""

from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ToolCall

type ToolCallStatus = Literal["success", "error", "denied"]


async def create(
    session: AsyncSession,
    *,
    run_id: UUID,
    agent: str,
    tool: str,
    args_hash: str,
    duration_ms: int,
    status: ToolCallStatus,
    cost: float | None = None,
    error: str | None = None,
) -> ToolCall:
    """Append one audit row; callers own the transaction that makes it durable."""
    row = ToolCall(
        run_id=run_id,
        agent=agent,
        tool=tool,
        args_hash=args_hash,
        duration_ms=duration_ms,
        status=status,
        cost=cost,
        error=error,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row
