"""Immutable campaign version snapshots and their append-only guard.

Revisions create a new row linked by parent_version_id; no prior version is ever
rewritten. The guard here covers ORM flushes. Bulk ``UPDATE``/``DELETE`` bypasses
mapper events, so a database trigger belongs in the migration step.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import (
    Base,
    CreatedAtMixin,
    ImmutableRowError,
    UUIDPrimaryKeyMixin,
    guard_immutable,
)

PackagePayload = dict[str, Any]


class ImmutableVersionError(ImmutableRowError):
    """Raised when a persisted campaign version is updated or deleted."""


class CampaignVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One immutable package snapshot for a campaign."""

    __tablename__ = "campaign_versions"
    __table_args__ = (
        Index("ix_campaign_versions_campaign_id_version", "campaign_id", "version", unique=True),
    )

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaign_versions.id"), index=True
    )
    package: Mapped[PackagePayload] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float)


guard_immutable(CampaignVersion, ImmutableVersionError)
