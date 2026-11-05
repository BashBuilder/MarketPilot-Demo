"""Supervisor Agent: deterministic routing for the workflow graph.

The Supervisor never calls an LLM. It reads the latest validated state and
returns the next node, so the same state always produces the same decision.
The only mutation is advancing the automatic low-score loop counter, which the
graph node persists with the next checkpoint.
"""

from app.agents.outputs import RouteDecision
from app.agents.scoring import weakest_node
from app.agents.supervisor_rules import (
    AUTO_LOOP_KEY,
    advance_loops,
    any_copy_failure,
    auto_loops,
    failed_items,
    human_decision,
    is_retry_exhausted,
)
from app.core.config import Settings, get_settings
from app.graph.state import WorkflowState

__all__ = ["AUTO_LOOP_KEY", "route"]


def route(state: WorkflowState, *, settings: Settings | None = None) -> RouteDecision:
    """Return the next node for ``state`` without an LLM call."""
    limits = settings or get_settings()

    human = human_decision(state)
    if human is not None:
        return human

    if any(is_retry_exhausted(error) for error in state.errors):
        return RouteDecision(
            next_node="human",
            reason="A node exhausted its retry budget; escalating to a human.",
            escalate=True,
        )

    failed = failed_items(state)
    if failed:
        if any_copy_failure(failed, state):
            return RouteDecision(
                next_node="copywriter",
                reason=(
                    f"Compliance failed {len(failed)} item(s) including copy; "
                    "revising the copy first."
                ),
            )
        return RouteDecision(
            next_node="designer",
            reason=(
                f"Compliance failed {len(failed)} item(s) with no copy item; "
                "revising the visual assets."
            ),
        )

    score = state.score
    if score is not None and score.total < limits.score_threshold:
        loops = auto_loops(state)
        if loops < limits.max_auto_loops:
            next_node = weakest_node(score)
            new_loops = advance_loops(state)
            return RouteDecision(
                next_node=next_node,
                reason=(
                    f"Score {score.total:.2f} is below threshold "
                    f"{limits.score_threshold}; automatic loop {new_loops} of "
                    f"{limits.max_auto_loops} reruns {next_node}."
                ),
            )
        return RouteDecision(
            next_node="human",
            reason=(
                f"Score {score.total:.2f} is below threshold "
                f"{limits.score_threshold} after {loops} automatic loop(s); "
                "escalating to a human."
            ),
            escalate=True,
        )

    return RouteDecision(
        next_node="human",
        reason="The package is ready for the human approval gate.",
    )
