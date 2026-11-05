"""Creative score model: the reviewer's per-dimension verdict for a version."""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

ScoreBreakdown = dict[str, Any]


class CreativeScore(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One weighted score out of 100, with per-dimension justifications."""

    __tablename__ = "creative_scores"
    __table_args__ = (
        Index("ix_creative_scores_campaign_version_id", "campaign_version_id", unique=True),
    )

    campaign_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_versions.id"), nullable=False
    )
    breakdown: Mapped[ScoreBreakdown] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    total: Mapped[float] = mapped_column(Float, nullable=False)
