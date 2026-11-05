"""LangGraph wiring for the campaign pipeline and its supervised loops.

The happy path runs one pass to the human gate. Compliance can send the graph
back to copy or visuals, and a low score can send it to the weakest node for at
most the configured number of automatic loops. Escalations bypass the rest of
the pipeline and go straight to the human gate.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import LLMClient, ToolInvoker
from app.core.config import Settings, get_settings
from app.graph.node_support import NodeEventEmitter
from app.graph.nodes import NodeAgent, NodeDependencies, WorkflowNode, make_node
from app.graph.routing import (
    APPROVAL_NODE,
    LOOP_PREFIX,
    PIPELINE,
    compliance_map,
    following_node,
    guard_map,
    make_compliance_router,
    make_guard,
    make_loop_node,
    make_reviewer_router,
    reviewer_map,
)
from app.graph.state import WorkflowState
from app.harness.checkpoints import request_approval
from app.harness.registry import AgentName


@dataclass(frozen=True, slots=True)
class WorkflowDependencies:
    """Run-scoped services shared by every node in one graph invocation."""

    run_id: UUID
    llm: LLMClient
    session: AsyncSession
    emit: NodeEventEmitter
    tools: Mapping[AgentName, ToolInvoker]
    settings: Settings | None = None


def build_workflow(
    agents: Mapping[AgentName, NodeAgent],
    deps: WorkflowDependencies,
) -> CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState]:
    """Compile the pipeline, its supervised loops and the human gate."""
    missing = [name for name in PIPELINE if name not in agents]
    if missing:
        raise ValueError(f"missing agents for pipeline: {missing}")

    limits = deps.settings or get_settings()
    builder = StateGraph(WorkflowState)
    node_deps = {
        name: NodeDependencies(
            run_id=deps.run_id,
            llm=deps.llm,
            session=deps.session,
            emit=deps.emit,
            tools=deps.tools.get(name),
            settings=deps.settings,
        )
        for name in PIPELINE
    }

    for name in PIPELINE:
        builder.add_node(name, make_node(agents[name], node_deps[name]))
        builder.add_node(f"{LOOP_PREFIX}{name}", make_loop_node(agents[name], node_deps[name]))

    builder.add_node(APPROVAL_NODE, _make_approval_node(deps))
    builder.add_edge(START, PIPELINE[0])
    for current, _ in pairwise(PIPELINE):
        if current == "compliance":
            continue
        builder.add_conditional_edges(
            current,
            make_guard(following_node(current)),
            guard_map(following_node(current)),
        )

    builder.add_conditional_edges("compliance", make_compliance_router(limits), compliance_map())
    builder.add_conditional_edges("reviewer", make_reviewer_router(limits), reviewer_map())

    for name in PIPELINE:
        loop_name = f"{LOOP_PREFIX}{name}"
        if name == "compliance":
            builder.add_conditional_edges(
                loop_name, make_compliance_router(limits), compliance_map()
            )
        elif name == "reviewer":
            builder.add_conditional_edges(loop_name, make_reviewer_router(limits), reviewer_map())
        else:
            following = following_node(name)
            builder.add_conditional_edges(
                loop_name,
                make_guard(following),
                guard_map(following),
            )

    builder.add_edge(APPROVAL_NODE, END)
    return builder.compile()


def _make_approval_node(deps: WorkflowDependencies) -> WorkflowNode:
    """Persist the human gate and expose it as the graph's terminal state."""

    async def approval(state: WorkflowState) -> WorkflowState:
        await request_approval(deps.session, deps.run_id)
        state.status = "awaiting_approval"
        return state

    return approval
