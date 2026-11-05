"""Copywriter Agent: original and revision copy under policy guardrails."""

import json
import re

from pydantic import TypeAdapter

from app.agents.base import AgentPreparation, BaseAgent, ToolInvoker
from app.agents.outputs import AdCopySet, ComplianceItem
from app.core.config import Settings
from app.core.errors import ToolError, ValidationFailure
from app.graph.state import WorkflowState
from app.harness.guardrails import delimit_untrusted
from app.harness.registry import AgentName
from app.harness.validators import Issue
from app.harness.verification import CopySemanticValidator, Validator
from app.tools.policy_models import PolicyLookupArgs, PolicyMatch
from app.tools.policy_tools import POLICY_TOOL_NAME

__all__ = ["CopyRevisionValidator", "CopywriterAgent"]

_VARIANT_INDEX = re.compile(r"variant\s+(\d+)", re.IGNORECASE)
_POLICY_MATCHES = TypeAdapter(list[PolicyMatch])


class CopyRevisionValidator:
    """Keep every unflagged variant exactly as it was before the revision."""

    def __init__(self, previous: AdCopySet, flagged: frozenset[int]) -> None:
        self._previous = tuple(previous.variants)
        self._flagged = flagged

    def validate(self, value: AdCopySet) -> list[Issue]:
        if len(value.variants) != len(self._previous):
            return [
                f"revision returned {len(value.variants)} variants; "
                f"keep all {len(self._previous)} and change only flagged ones"
            ]
        issues: list[Issue] = []
        pairs = zip(self._previous, value.variants, strict=True)
        for index, (before, after) in enumerate(pairs, start=1):
            if index not in self._flagged and after != before:
                issues.append(
                    f"variant {index} ({before.channel}) is not flagged but was changed; "
                    "keep it identical to the previous copy"
                )
        return issues


class CopywriterAgent(BaseAgent[AdCopySet]):
    """Write copy, or revise only the variants compliance flagged."""

    name: AgentName = "copywriter"
    output_model = AdCopySet
    prompt_name = "copywriter"
    validators = (CopySemanticValidator(),)

    async def prepare(
        self,
        state: WorkflowState,
        tools: ToolInvoker | None,
        *,
        settings: Settings | None = None,
    ) -> AgentPreparation[AdCopySet]:
        del settings
        failed = _failed_items(state)
        previous = state.copy if failed else None
        if failed and previous is None:
            raise ValidationFailure("copywriter revision requires the current copy")

        validators: tuple[Validator[AdCopySet], ...] = ()
        if failed and previous is not None:
            flagged = _flagged_indices(failed, len(previous.variants))
            validators = (CopyRevisionValidator(previous, flagged),)

        policy_context = await self._policy_context(state, failed, tools)
        return AgentPreparation(context=policy_context, validators=validators)

    def _context_block(self, state: WorkflowState) -> str:
        failed = _failed_items(state)
        if not failed:
            return super()._context_block(state)
        previous = state.copy
        if previous is None:
            raise ValidationFailure("copywriter revision requires the current copy")
        payload = {
            "failed_items": [item.model_dump(mode="json") for item in failed],
            "current_copy": previous.model_dump(mode="json"),
        }
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return delimit_untrusted(text, source="revision-context")

    async def _policy_context(
        self,
        state: WorkflowState,
        failed: tuple[ComplianceItem, ...],
        tools: ToolInvoker | None,
    ) -> str:
        if tools is None:
            raise ToolError("copywriter requires the policy_lookup tool middleware")
        args = PolicyLookupArgs(query=_policy_query(state, failed), top_k=3)
        raw = await tools.call(POLICY_TOOL_NAME, args.model_dump())
        matches = _POLICY_MATCHES.validate_python(raw)
        return json.dumps(
            [match.model_dump(mode="json") for match in matches],
            ensure_ascii=False,
            sort_keys=True,
        )


def _failed_items(state: WorkflowState) -> tuple[ComplianceItem, ...]:
    if state.compliance is None:
        return ()
    return tuple(item for item in state.compliance.items if not item.passed)


def _flagged_indices(failed: tuple[ComplianceItem, ...], variant_count: int) -> frozenset[int]:
    found: set[int] = set()
    for item in failed:
        for text in (item.check, item.reason):
            found.update(int(match) for match in _VARIANT_INDEX.findall(text))
    in_range = {index for index in found if 1 <= index <= variant_count}
    # A failure with no variant marker is global; allow every variant to change.
    return frozenset(in_range) if in_range else frozenset(range(1, variant_count + 1))


def _policy_query(state: WorkflowState, failed: tuple[ComplianceItem, ...]) -> str:
    parts = [state.idea]
    if failed:
        parts.extend(f"{item.check}: {item.reason}" for item in failed)
    else:
        if state.brief is not None:
            parts.extend([state.brief.product, state.brief.goal, state.brief.audience])
        if state.research is not None:
            parts.extend(state.research.messaging_angles)
    query = " ".join(part for part in parts if part).strip()[:500]
    return query if len(query) >= 2 else "advertising policy"
