"""Compliance report model: one pass/fail verdict per version."""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

ComplianceItems = list[dict[str, Any]]


class ComplianceReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable item-level compliance findings for a campaign version."""

    __tablename__ = "compliance_reports"
    __table_args__ = (
        Index("ix_compliance_reports_campaign_version_id", "campaign_version_id", unique=True),
    )

    campaign_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_versions.id"), nullable=False
    )
    items: Mapped[ComplianceItems] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
