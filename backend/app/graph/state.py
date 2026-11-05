"""Shared workflow state and the agent-output validation boundary."""

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.agents.outputs import (
    AdCopySet,
    AssetSet,
    AudienceResearch,
    CampaignBrief,
    ComplianceReport,
    CreativeDirection,
    CreativeScore,
)
from app.core.errors import ValidationFailure

WorkflowStatus = Literal[
    "pending",
    "running",
    "awaiting_approval",
    "approved",
    "revising",
    "completed",
    "failed",
]


class WorkflowState(BaseModel):
    """Everything a node needs, plus the versions and failures produced so far.

    State is mutable because node wrappers merge validated outputs into it;
    each individual output model stays frozen.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    idea: Annotated[str, Field(min_length=5)]
    brief: CampaignBrief | None = None
    research: AudienceResearch | None = None
    # BaseModel.copy() is deprecated, but mypy still sees it as a method; the
    # state field intentionally shadows it because nodes read ``state.copy``.
    copy: AdCopySet | None = None  # type: ignore[assignment]
    direction: CreativeDirection | None = None
    assets: AssetSet | None = None
    compliance: ComplianceReport | None = None
    score: CreativeScore | None = None

    versions: list[Annotated[int, Field(ge=1)]] = Field(default_factory=list)
    status: WorkflowStatus = "pending"
    retry_counters: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    @field_validator("versions")
    @classmethod
    def _versions_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("versions must be unique")
        return value

    @field_validator("retry_counters")
    @classmethod
    def _retry_counters_valid(cls, value: dict[str, int]) -> dict[str, int]:
        for node, count in value.items():
            if not node.strip():
                raise ValueError("retry counter keys must not be blank")
            if count < 0:
                raise ValueError("retry counters must be non-negative")
        return value


def parse_agent_output[TOutput: BaseModel](
    model: type[TOutput], payload: Mapping[str, Any], *, agent: str
) -> TOutput:
    """Validate an agent output and translate schema errors for the harness."""
    try:
        return model.model_validate(dict(payload))
    except ValidationError as exc:
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors(include_url=False)
        ]
        raise ValidationFailure(
            f"{agent} produced invalid output",
            details={"agent": agent, "errors": errors},
        ) from exc
