"""Reviewer Agent: score the package without approving or exporting it."""

import json

from pydantic import TypeAdapter

from app.agents.base import AgentPreparation, BaseAgent, ToolInvoker
from app.agents.outputs import CreativeScore
from app.agents.scoring import weighted_total
from app.core.config import Settings
from app.core.errors import ToolError
from app.graph.state import WorkflowState
from app.harness.registry import AgentName
from app.harness.validators import Issue
from app.tools.policy_models import PolicyLookupArgs, PolicyMatch
from app.tools.policy_tools import POLICY_TOOL_NAME

__all__ = ["ReviewScoreValidator", "ReviewerAgent"]

_POLICY_MATCHES = TypeAdapter(list[PolicyMatch])


class ReviewScoreValidator:
    """Re-check the rubric at the agent boundary.

    Presence and 0..10 bounds are guaranteed by ``CreativeScore``; this keeps
    the weighted-total rule explicit so the retry feedback stays stable if the
    model constraint is ever relaxed.
    """

    def validate(self, value: CreativeScore) -> list[Issue]:
        dimensions = {
            "brief_alignment": value.brief_alignment,
            "audience_fit": value.audience_fit,
            "copy_quality": value.copy_quality,
            "visual_quality": value.visual_quality,
            "compliance_risk": value.compliance_risk,
        }
        issues: list[Issue] = []
        for name, dimension in dimensions.items():
            if not dimension.justification.strip():
                issues.append(f"{name}: justification must not be empty")

        expected = weighted_total({name: dimension.score for name, dimension in dimensions.items()})
        if abs(value.total - expected) > 0.01:
            issues.append(f"total {value.total} must equal the weighted dimensions ({expected})")
        return issues


class ReviewerAgent(BaseAgent[CreativeScore]):
    """Score every dimension and recommend revisions, never approval."""

    name: AgentName = "reviewer"
    output_model = CreativeScore
    prompt_name = "reviewer"
    validators = (ReviewScoreValidator(),)

    async def prepare(
        self,
        state: WorkflowState,
        tools: ToolInvoker | None,
        *,
        settings: Settings | None = None,
    ) -> AgentPreparation[CreativeScore]:
        del settings
        if tools is None:
            raise ToolError("reviewer requires the policy_lookup tool middleware")

        args = PolicyLookupArgs(query=_policy_query(state), top_k=3)
        raw = await tools.call(POLICY_TOOL_NAME, args.model_dump())
        matches = _POLICY_MATCHES.validate_python(raw)
        context = json.dumps(
            [match.model_dump(mode="json") for match in matches],
            ensure_ascii=False,
            sort_keys=True,
        )
        return AgentPreparation(context=context)


def _policy_query(state: WorkflowState) -> str:
    parts = [state.idea]
    if state.brief is not None:
        parts.extend([state.brief.product, state.brief.goal, state.brief.audience])
    if state.copy is not None:
        parts.extend(f"{variant.headline} {variant.description}" for variant in state.copy.variants)
    if state.compliance is not None:
        parts.extend(f"{item.check}: {item.reason}" for item in state.compliance.items)
    query = " ".join(part for part in parts if part).strip()[:500]
    return query if len(query) >= 2 else "advertising policy"
