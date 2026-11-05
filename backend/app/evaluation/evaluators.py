"""Pure metrics used by the offline evaluation runner.

Each function takes already-collected outputs or verdicts and returns a result
without touching the database, network, filesystem or environment. That keeps
regressions deterministic and lets the runner use fakes.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from pydantic import BaseModel, ValidationError

from app.agents.outputs import (
    AdCopySet,
    AssetSet,
    AudienceResearch,
    CampaignBrief,
    ComplianceReport,
    CreativeDirection,
    CreativeScore,
    RouteDecision,
)
from app.evaluation.datasets import BadClaimCase, CleanCase

MAX_AUTO_LOOPS: Final[int] = 2

_OUTPUT_MODELS: Final[Mapping[str, type[BaseModel]]] = {
    "brief": CampaignBrief,
    "research": AudienceResearch,
    "copywriter": AdCopySet,
    "creative_director": CreativeDirection,
    "designer": AssetSet,
    "compliance": ComplianceReport,
    "reviewer": CreativeScore,
    "supervisor": RouteDecision,
}


@dataclass(frozen=True, slots=True)
class SchemaValidity:
    """How many raw agent outputs parsed against their output schemas."""

    passed: int
    total: int
    failing_agents: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecallResult:
    """Compliance recall overall and split by the rule each case violates."""

    overall: float
    per_rule: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class LoopEvent:
    """A checkpoint snapshot carrying the run's automatic-loop counter."""

    auto_loops: int


def schema_validity(raw_outputs: Mapping[str, object]) -> SchemaValidity:
    """Validate each raw output against the model owned by its agent."""
    failing: list[str] = []
    for agent, raw in raw_outputs.items():
        model = _OUTPUT_MODELS.get(agent)
        if model is None:
            failing.append(agent)
            continue
        try:
            model.model_validate(raw)
        except ValidationError:
            failing.append(agent)
    return SchemaValidity(
        passed=len(raw_outputs) - len(failing),
        total=len(raw_outputs),
        failing_agents=tuple(sorted(failing)),
    )


def compliance_recall(cases: Sequence[BadClaimCase], results: Mapping[str, bool]) -> RecallResult:
    """Measure the share of bad claims compliance correctly rejected.

    ``results`` maps case ids to compliance verdicts, where ``True`` means the
    case was flagged as failing. A missing verdict counts as not caught.
    """
    if not cases:
        return RecallResult(overall=0.0, per_rule={})

    by_rule: dict[str, list[bool]] = {}
    for case in cases:
        by_rule.setdefault(case.violated_rule, []).append(results.get(case.id, False))

    caught = sum(sum(verdicts) for verdicts in by_rule.values())
    per_rule = {rule: sum(verdicts) / len(verdicts) for rule, verdicts in by_rule.items()}
    return RecallResult(overall=caught / len(cases), per_rule=per_rule)


def compliance_false_positive_rate(
    cases: Sequence[CleanCase], results: Mapping[str, bool]
) -> float:
    """Measure the share of clean claims compliance wrongly flagged."""
    if not cases:
        return 0.0
    flagged = sum(1 for case in cases if results.get(case.id, False))
    return flagged / len(cases)


def score_spread(scores: Sequence[float]) -> float:
    """Return max minus min across repeated scores for the same package."""
    if not scores:
        return 0.0
    return max(scores) - min(scores)


def stable(scores: Sequence[float], max_spread: float) -> bool:
    """Return whether repeated scores stay within the allowed spread."""
    return score_spread(scores) <= max_spread


def loop_behavior(events: Iterable[LoopEvent], max_auto_loops: int = MAX_AUTO_LOOPS) -> bool:
    """Return whether every recorded checkpoint stayed within the loop cap."""
    return all(event.auto_loops <= max_auto_loops for event in events)
