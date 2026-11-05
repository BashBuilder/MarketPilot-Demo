"""Event and state helpers shared by graph nodes."""

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.agents.contracts import EventEmitter
from app.agents.outputs import RouteDecision
from app.graph.state import WorkflowState
from app.harness.registry import AgentName
from app.harness.verification import VerificationEvent

type NodeEventEmitter = Callable[[str, Mapping[str, Any]], Awaitable[None]]

# Each pipeline agent owns exactly one package field on WorkflowState. The
# Supervisor routes instead of producing a package field, so it is absent.
OUTPUT_FIELDS: Mapping[AgentName, str] = {
    "brief": "brief",
    "research": "research",
    "copywriter": "copy",
    "creative_director": "direction",
    "designer": "assets",
    "compliance": "compliance",
    "reviewer": "score",
}

_NEXT_NODE: Mapping[AgentName, str] = {
    "brief": "research",
    "research": "copywriter",
    "copywriter": "creative_director",
    "creative_director": "designer",
    "designer": "compliance",
    "compliance": "reviewer",
    "reviewer": "human",
}


def event_payload(run_id: UUID, agent: str) -> dict[str, Any]:
    """Build the common envelope required by every SSE event."""
    return {
        "run_id": str(run_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "agent": agent,
    }


def verification_event_emitter(emit: NodeEventEmitter, *, run_id: UUID, agent: str) -> EventEmitter:
    """Adapt harness verification events to the node's injected emitter."""

    async def relay(event: VerificationEvent) -> None:
        data = event_payload(run_id, agent)
        data.update(
            {
                "attempt": event.attempt,
                "max_attempts": event.max_attempts,
                "issues": list(event.issues),
                "reason": "; ".join(event.issues),
            }
        )
        if event.delay is not None:
            data["delay"] = event.delay
        await emit(event.event, data)

    return relay


def merge_output(state: WorkflowState, agent: AgentName, output: BaseModel) -> None:
    """Write a validated output into its mapped state field.

    The Supervisor deliberately has no mapped field; its route decision is
    consumed by the graph edges instead of being merged into package state.
    """
    field = OUTPUT_FIELDS.get(agent)
    if field is not None:
        setattr(state, field, output)


def handoff_target(agent: AgentName, output: BaseModel) -> str:
    """Return the node receiving the handoff after a successful agent run."""
    if isinstance(output, RouteDecision):
        return output.next_node
    return _NEXT_NODE.get(agent, "human")
