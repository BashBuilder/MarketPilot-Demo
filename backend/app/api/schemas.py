"""HTTP schemas mirroring the API contract in section 2 of agent.md."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import CampaignStatus


class CreateCampaignRequest(BaseModel):
    """Body of ``POST /campaigns``."""

    model_config = ConfigDict(extra="forbid")

    idea: str


class CampaignCreated(BaseModel):
    """Response for a campaign that was durably created and launched."""

    campaign_id: UUID
    run_id: UUID


class CampaignSummary(BaseModel):
    """Campaign list item and the top of the campaign detail response."""

    id: UUID
    idea: str
    status: CampaignStatus
    latest_version: int | None
    latest_score: float | None
    active_run_id: UUID | None
    created_at: datetime
    updated_at: datetime


class VersionSummary(BaseModel):
    """One append-only version in a campaign's history."""

    model_config = ConfigDict(from_attributes=True)

    version: int
    parent_version_id: UUID | None
    score: float | None
    created_at: datetime


class CampaignPackage(BaseModel):
    """The full package snapshot stored for one version."""

    model_config = ConfigDict(extra="allow")

    brief: dict[str, Any] | None = None
    research: dict[str, Any] | None = None
    # ``BaseModel.copy`` is deprecated but mypy still sees it as a method.
    copy: dict[str, Any] | None = None  # type: ignore[assignment]
    direction: dict[str, Any] | None = None
    assets: dict[str, Any] | None = None
    compliance: dict[str, Any] | None = None
    score: dict[str, Any] | None = None


class DiffChange(BaseModel):
    """One changed leaf field with its values on each side."""

    path: str
    before: Any
    after: Any


class VersionDiff(BaseModel):
    """Changed fields between two versions, matching ``compute_diff``."""

    model_config = ConfigDict(populate_by_name=True)

    from_version: int = Field(alias="from")
    to_version: int = Field(alias="to")
    changes: list[DiffChange]


class ApproveRequest(BaseModel):
    """Body of ``POST /runs/{run_id}/approve``."""

    model_config = ConfigDict(extra="forbid")

    comment: str | None = None


class ReviseRequest(BaseModel):
    """Body of ``POST /runs/{run_id}/revise``."""

    model_config = ConfigDict(extra="forbid")

    comment: str
    target_node: str | None = None


class ErrorDetail(BaseModel):
    """Machine-readable error body with optional structured context."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Envelope used by every error response."""

    error: ErrorDetail
