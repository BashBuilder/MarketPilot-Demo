"""Routing helpers for compliance failures, low scores and escalation.

Supervisor decisions are computed in conditional edges. LangGraph discards
state mutations made there, so each automatic loop runs a loop-entry node that
increments the counter in the real graph state before invoking the agent.
"""

from collections.abc import Callable, Hashable, Mapping

from app.agents.supervisor import AUTO_LOOP_KEY, route
from app.agents.supervisor_rules import auto_loops
from app.core.config import Settings
from app.graph.nodes import NodeAgent, NodeDependencies, WorkflowNode, make_node
from app.graph.state import WorkflowState
from app.harness.registry import AgentName

PIPELINE: tuple[AgentName, ...] = (
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
)
APPROVAL_NODE = "approval"
LOOP_PREFIX = "loop_"

type NodeRouter = Callable[[WorkflowState], str]

_FOLLOWING: Mapping[AgentName, str] = {
    "brief": "research",
    "research": "copywriter",
    "copywriter": "creative_director",
    "creative_director": "designer",
    "designer": "compliance",
    "compliance": "reviewer",
    "reviewer": APPROVAL_NODE,
    "supervisor": APPROVAL_NODE,
}


def following_node(name: AgentName) -> str:
    """Return the normal next node after ``name`` in pipeline order."""
    return _FOLLOWING[name]


def guard_map(next_node: str) -> dict[Hashable, str]:
    """Path map that lets an escalated node jump over the next agent."""
    paths: dict[Hashable, str] = {next_node: next_node, APPROVAL_NODE: APPROVAL_NODE}
    return paths


def compliance_map() -> dict[Hashable, str]:
    # Loop-entry nodes increment the shared automatic-loop counter; routing
    # straight to the agent would let a persistent failure loop forever.
    paths: dict[Hashable, str] = {
        f"{LOOP_PREFIX}copywriter": f"{LOOP_PREFIX}copywriter",
        f"{LOOP_PREFIX}designer": f"{LOOP_PREFIX}designer",
        "reviewer": "reviewer",
        APPROVAL_NODE: APPROVAL_NODE,
    }
    return paths


def reviewer_map() -> dict[Hashable, str]:
    """Every pipeline target gets a loop-entry node so its counter advances."""
    paths: dict[Hashable, str] = {
        f"{LOOP_PREFIX}{name}": f"{LOOP_PREFIX}{name}" for name in PIPELINE
    }
    paths[APPROVAL_NODE] = APPROVAL_NODE
    return paths


def make_guard(next_node: str) -> NodeRouter:
    """Continue normally unless a node escalated and must reach a human."""

    def choose(state: WorkflowState) -> str:
        return APPROVAL_NODE if state.status == "escalated" else next_node

    return choose


def make_compliance_router(settings: Settings) -> NodeRouter:
    """Loop back only when compliance found copy or visual failures.

    A low score from an earlier reviewer pass is still in state while a
    compliance loop runs. Without the explicit failure check, ``route`` would
    keep choosing that stale score's weakest node instead of moving on.
    Compliance loops share the automatic-loop budget, so a failure that never
    clears escalates to the human instead of rerunning the pipeline forever.
    """

    def choose(state: WorkflowState) -> str:
        decision = route(state, settings=settings)
        if state.status == "escalated":
            return APPROVAL_NODE
        if not _has_compliance_failures(state):
            return "reviewer"
        if decision.escalate:
            return APPROVAL_NODE
        if decision.next_node not in {"copywriter", "designer"}:
            return "reviewer"
        if auto_loops(state) >= settings.max_auto_loops:
            return APPROVAL_NODE
        return f"{LOOP_PREFIX}{decision.next_node}"

    return choose


def _has_compliance_failures(state: WorkflowState) -> bool:
    return state.compliance is not None and any(not item.passed for item in state.compliance.items)


def make_reviewer_router(settings: Settings) -> NodeRouter:
    """Loop to the weakest node, or stop at the human gate."""

    def choose(state: WorkflowState) -> str:
        decision = route(state, settings=settings)
        target = decision.next_node
        if state.status == "escalated" or decision.escalate or target in {"human", "end"}:
            return APPROVAL_NODE
        if target in PIPELINE:
            return f"{LOOP_PREFIX}{target}"
        return APPROVAL_NODE

    return choose


def make_loop_node(agent: NodeAgent, deps: NodeDependencies) -> WorkflowNode:
    """Increment the automatic-loop counter, then run the target agent."""
    inner = make_node(agent, deps)

    async def loop(state: WorkflowState) -> WorkflowState:
        state.retry_counters[AUTO_LOOP_KEY] = state.retry_counters.get(AUTO_LOOP_KEY, 0) + 1
        return await inner(state)

    return loop
