"""Tool call model: immutable audit rows for every harness tool invocation."""

from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
    guard_immutable,
)


class ToolCall(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Outcome and cost of one tool invocation, keyed to its run."""

    __tablename__ = "tool_calls"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(32), nullable=False)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    args_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    cost: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)


guard_immutable(ToolCall)
