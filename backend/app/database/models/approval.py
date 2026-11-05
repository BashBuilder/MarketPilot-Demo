"""Approval model: the human decision on a generated campaign version."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ApprovalDecision(StrEnum):
    """Outcome of a human review."""

    APPROVE = "approve"
    REVISE = "revise"


def _decision_values(enum_cls: type[StrEnum]) -> list[str]:
    """Persist enum values rather than member names for readable rows."""
    return [str(member.value) for member in enum_cls]


class Approval(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An immutable audit entry for one approve or revise action."""

    __tablename__ = "approvals"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    campaign_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_versions.id"), nullable=False, index=True
    )
    decision: Mapped[ApprovalDecision] = mapped_column(
        SqlEnum(
            ApprovalDecision,
            native_enum=False,
            length=16,
            validate_strings=True,
            values_callable=_decision_values,
        ),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    target_node: Mapped[str | None] = mapped_column(String(64))
