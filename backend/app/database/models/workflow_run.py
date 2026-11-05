"""Workflow run model: one execution of the agent graph for a campaign."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RunStatus(StrEnum):
    """Lifecycle of a single graph run."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


def _status_values(enum_cls: type[StrEnum]) -> list[str]:
    """Persist enum values rather than member names for readable rows."""
    return [str(member.value) for member in enum_cls]


class WorkflowRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks which node a run is on and how it ended."""

    __tablename__ = "workflow_runs"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id"), nullable=False, index=True
    )
    status: Mapped[RunStatus] = mapped_column(
        SqlEnum(
            RunStatus,
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=_status_values,
        ),
        nullable=False,
        default=RunStatus.PENDING,
        server_default=RunStatus.PENDING.value,
    )
    current_node: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
