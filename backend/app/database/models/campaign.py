"""Campaign model: one user-submitted idea and its lifecycle status."""

from enum import StrEnum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CampaignStatus(StrEnum):
    """Lifecycle of a campaign across all of its runs."""

    DRAFT = "draft"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


def _status_values(enum_cls: type[StrEnum]) -> list[str]:
    """Persist enum values rather than member names for readable rows."""
    return [str(member.value) for member in enum_cls]


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The durable record of a campaign idea."""

    __tablename__ = "campaigns"

    idea: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        SqlEnum(
            CampaignStatus,
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=_status_values,
        ),
        nullable=False,
        default=CampaignStatus.DRAFT,
        server_default=CampaignStatus.DRAFT.value,
    )
