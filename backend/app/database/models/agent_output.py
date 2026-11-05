"""Agent output model: immutable validated results written by graph nodes."""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
    guard_immutable,
)

AgentPayload = dict[str, Any]


class AgentOutput(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single agent's validated output for one handoff."""

    __tablename__ = "agent_outputs"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(32), nullable=False)
    output: Mapped[AgentPayload] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )


guard_immutable(AgentOutput)
