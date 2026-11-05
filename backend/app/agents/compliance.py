"""Compliance Agent: flag risky claims without rewriting the work."""

import json

from pydantic import TypeAdapter

from app.agents.base import AgentPreparation, BaseAgent, ToolInvoker
from app.agents.outputs import ComplianceReport
from app.core.config import Settings
from app.core.errors import ToolError
from app.graph.state import WorkflowState
from app.harness.registry import AgentName
from app.tools.policy_models import PolicyLookupArgs, PolicyMatch
from app.tools.policy_tools import POLICY_TOOL_NAME

__all__ = ["ComplianceAgent"]

_POLICY_MATCHES = TypeAdapter(list[PolicyMatch])


class ComplianceAgent(BaseAgent[ComplianceReport]):
    """Check claims against retrieved policy, flagging rather than editing."""

    name: AgentName = "compliance"
    output_model = ComplianceReport
    prompt_name = "compliance"

    async def prepare(
        self,
        state: WorkflowState,
        tools: ToolInvoker | None,
        *,
        settings: Settings | None = None,
    ) -> AgentPreparation[ComplianceReport]:
        del settings
        if tools is None:
            raise ToolError("compliance requires the policy_lookup tool middleware")

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
        parts.extend(state.brief.constraints)
    if state.copy is not None:
        parts.extend(f"{variant.headline} {variant.description}" for variant in state.copy.variants)
    query = " ".join(part for part in parts if part).strip()[:500]
    return query if len(query) >= 2 else "advertising policy"
