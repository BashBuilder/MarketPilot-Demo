"""Workflow checkpoint model: persisted graph state after each node."""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

CheckpointState = dict[str, Any]


class WorkflowCheckpoint(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One state snapshot, ordered by step within a run."""

    __tablename__ = "workflow_checkpoints"
    __table_args__ = (Index("ix_workflow_checkpoints_run_id_step", "run_id", "step", unique=True),)

    run_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    node: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[CheckpointState] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
