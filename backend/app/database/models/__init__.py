"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.database.models.agent_output import AgentOutput
from app.database.models.approval import Approval, ApprovalDecision
from app.database.models.asset import Asset, AssetKind
from app.database.models.base import (
    Base,
    CreatedAtMixin,
    ImmutableRowError,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    guard_immutable,
)
from app.database.models.campaign import Campaign, CampaignStatus
from app.database.models.campaign_version import (
    CampaignVersion,
    ImmutableVersionError,
    PackagePayload,
)
from app.database.models.compliance_report import ComplianceReport
from app.database.models.creative_score import CreativeScore
from app.database.models.policy_document import (
    EMBEDDING_DIMENSIONS,
    PolicyDocument,
    PolicyMetadata,
)
from app.database.models.tool_call import ToolCall
from app.database.models.workflow_checkpoint import WorkflowCheckpoint
from app.database.models.workflow_run import RunStatus, WorkflowRun

__all__ = [
    "EMBEDDING_DIMENSIONS",
    "AgentOutput",
    "Approval",
    "ApprovalDecision",
    "Asset",
    "AssetKind",
    "Base",
    "Campaign",
    "CampaignStatus",
    "CampaignVersion",
    "ComplianceReport",
    "CreatedAtMixin",
    "CreativeScore",
    "ImmutableRowError",
    "ImmutableVersionError",
    "PackagePayload",
    "PolicyDocument",
    "PolicyMetadata",
    "RunStatus",
    "TimestampMixin",
    "ToolCall",
    "UUIDPrimaryKeyMixin",
    "WorkflowCheckpoint",
    "WorkflowRun",
    "guard_immutable",
]
