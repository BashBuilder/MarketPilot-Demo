"""Deterministic predicates and counters used by the Supervisor."""

import re
from collections.abc import Sequence
from typing import Final

from app.agents.outputs import AgentNode, ComplianceItem, RouteDecision
from app.agents.scoring import weakest_node
from app.graph.state import WorkflowState

AUTO_LOOP_KEY: Final[str] = "auto_loops"

_COPY_MARKERS: Final[re.Pattern[str]] = re.compile(
    r"\b(?:copy|variant|headline|description|cta|wording|claim)\b",
    re.IGNORECASE,
)
_REVISION_NODES: Final[frozenset[str]] = frozenset(
    {
        "brief",
        "research",
        "copywriter",
        "creative_director",
        "designer",
        "compliance",
        "reviewer",
    }
)


def human_decision(state: WorkflowState) -> RouteDecision | None:
    """Resolve an approval or revision the human already recorded."""
    if state.status in ("approved", "completed"):
        return RouteDecision(
            next_node="end",
            reason="The human approved the package; the run is complete.",
        )
    if state.status != "revising":
        return None

    chosen = state.target_node
    if chosen is not None and chosen in _REVISION_NODES:
        return RouteDecision(
            next_node=chosen,
            reason=f"The human chose to revise {chosen}.",
        )

    target = weakest_or_default(state)
    return RouteDecision(
        next_node=target,
        reason=f"The human requested a revision; routing to the weakest node ({target}).",
    )


def weakest_or_default(state: WorkflowState) -> AgentNode:
    """Use the weakest dimension, falling back to copy when no score exists."""
    if state.score is not None:
        return weakest_node(state.score)
    return "copywriter"


def failed_items(state: WorkflowState) -> tuple[ComplianceItem, ...]:
    if state.compliance is None:
        return ()
    return tuple(item for item in state.compliance.items if not item.passed)


def any_copy_failure(items: Sequence[ComplianceItem], state: WorkflowState) -> bool:
    for item in items:
        text = f"{item.check} {item.reason}"
        if _COPY_MARKERS.search(text) or _matches_copy(text, state):
            return True
    return False


def _matches_copy(text: str, state: WorkflowState) -> bool:
    if state.copy is None:
        return False
    lowered = text.casefold()
    for variant in state.copy.variants:
        values = (variant.channel, variant.headline, variant.description, variant.cta)
        if any(value.casefold() in lowered for value in values if value):
            return True
    return False


def is_retry_exhausted(error: str) -> bool:
    normalized = "".join(char for char in error.casefold() if char.isalnum())
    markers = (
        "retryexhausted",
        "retrybudgetexhausted",
        "failedverificationafter",
    )
    return any(marker in normalized for marker in markers)


def auto_loops(state: WorkflowState) -> int:
    return state.retry_counters.get(AUTO_LOOP_KEY, 0)


def advance_loops(state: WorkflowState) -> int:
    loops = auto_loops(state) + 1
    state.retry_counters = {**state.retry_counters, AUTO_LOOP_KEY: loops}
    return loops
