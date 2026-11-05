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
from app.agents.scoring import weakest_node
from app.core.config import Settings, get_settings
from app.core.errors import ValidationFailure
from app.database.models import ApprovalDecision, RunStatus
from app.database.repositories import campaigns, runs, versions
from app.graph.node_support import NodeEventEmitter, event_payload
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
from app.graph.versioning import snapshot_package
from app.harness.checkpoints import (
    DONE_NODE,
    load_latest_checkpoint,
    request_approval,
    resume_point,
    save_checkpoint,
    submit_decision,
)
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
    *,
    start_node: str = PIPELINE[0],
) -> CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState]:
    """Compile the pipeline, its supervised loops and the human gate.

    ``start_node`` lets a resume or a targeted revision enter the compiled
    graph at the node that still has work to do.
    """
    if start_node not in {*PIPELINE, APPROVAL_NODE}:
        raise ValueError(f"start_node must be a pipeline node or {APPROVAL_NODE!r}: {start_node!r}")
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
    builder.add_edge(START, start_node)
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


async def run_workflow(
    run_id: UUID,
    *,
    agents: Mapping[AgentName, NodeAgent],
    deps: WorkflowDependencies,
) -> WorkflowState:
    """Run or resume a run from its last checkpoint and stop at the human gate.

    A run that already completed or is waiting for approval is returned as-is,
    so calling this twice never replays agents. Each graph super-step is
    committed, which is what makes a crash after any node resumable.
    """
    _check_dependencies(run_id, deps)
    run = await runs.get(deps.session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    state = await load_latest_checkpoint(deps.session, run_id)
    if run.status in {RunStatus.AWAITING_APPROVAL, RunStatus.COMPLETED}:
        if state is None:
            raise ValidationFailure(
                f"run {run_id} has no checkpoint to return",
                details={"run_id": str(run_id)},
            )
        # The gate checkpoint stores the state written before the gate ran.
        state.status = "completed" if run.status is RunStatus.COMPLETED else "awaiting_approval"
        return state

    start_node: str
    if state is None:
        campaign = await campaigns.get(deps.session, run.campaign_id)
        if campaign is None:
            raise ValueError(f"campaign not found for run {run_id}")
        state = WorkflowState(idea=campaign.idea)
        start_node = PIPELINE[0]
    elif state.status == "escalated":
        # The escalation checkpoint was written just before the human gate.
        start_node = APPROVAL_NODE
    else:
        start_node = await resume_point(deps.session, run_id)
        if start_node == "human":
            start_node = APPROVAL_NODE
        elif start_node not in PIPELINE:
            return state

    return await _drive(
        run_id=run_id,
        agents=agents,
        deps=deps,
        start_node=start_node,
        state=state,
    )


async def continue_run(
    run_id: UUID,
    decision: ApprovalDecision | str,
    *,
    agents: Mapping[AgentName, NodeAgent],
    deps: WorkflowDependencies,
    comment: str | None = None,
    target_node: str | None = None,
) -> WorkflowState:
    """Record a human decision and drive the run to its next stop.

    Approval finishes the run and emits ``completed``. A revision reruns from
    the requested node, or from the weakest scoring dimension when no target is
    given, while all outputs produced before that node stay in state.
    """
    _check_dependencies(run_id, deps)
    run = await runs.get(deps.session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    state = await load_latest_checkpoint(deps.session, run_id)
    if state is None:
        raise ValidationFailure(
            f"run {run_id} has no checkpoint to continue from",
            details={"run_id": str(run_id)},
        )
    if run.status is RunStatus.COMPLETED:
        return state

    choice = ApprovalDecision(decision)
    resolved_target = target_node
    if choice is ApprovalDecision.REVISE and resolved_target is None and state.score is not None:
        resolved_target = weakest_node(state.score)

    next_node = await submit_decision(
        deps.session,
        run_id,
        choice,
        comment=comment,
        target_node=resolved_target,
    )

    if next_node == DONE_NODE:
        return await _complete(run_id, state, deps)

    state.status = "running"
    await deps.session.commit()
    return await _drive(
        run_id=run_id,
        agents=agents,
        deps=deps,
        start_node=next_node,
        state=state,
    )


async def _complete(
    run_id: UUID,
    state: WorkflowState,
    deps: WorkflowDependencies,
) -> WorkflowState:
    """Persist the approved state before announcing completion."""
    run = await runs.get(deps.session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    version = await versions.get_latest(deps.session, run.campaign_id)
    if version is None:
        raise ValidationFailure(
            f"run {run_id} has no campaign version to complete",
            details={"run_id": str(run_id)},
        )

    version_number = version.version
    score = state.score.total if state.score is not None else version.score
    state.status = "completed"
    await save_checkpoint(deps.session, run_id, DONE_NODE, state)
    await deps.session.commit()

    data = event_payload(run_id, "human")
    data.update({"version": version_number, "score": score})
    await deps.emit("completed", data)
    return state


async def _drive(
    *,
    run_id: UUID,
    agents: Mapping[AgentName, NodeAgent],
    deps: WorkflowDependencies,
    start_node: str,
    state: WorkflowState,
) -> WorkflowState:
    """Run the graph from ``start_node`` and commit after every super-step."""
    state.status = "running"
    await runs.set_status(deps.session, run_id, RunStatus.RUNNING, current_node=start_node)
    await deps.session.commit()

    graph = build_workflow(agents, deps, start_node=start_node)
    latest = state
    async for snapshot in graph.astream(state, stream_mode="values"):
        latest = (
            snapshot
            if isinstance(snapshot, WorkflowState)
            else WorkflowState.model_validate(snapshot)
        )
        await deps.session.commit()
    return latest


def _check_dependencies(run_id: UUID, deps: WorkflowDependencies) -> None:
    if deps.run_id != run_id:
        raise ValueError("workflow dependencies belong to a different run")


def _make_approval_node(deps: WorkflowDependencies) -> WorkflowNode:
    """Persist the human gate and expose it as the graph's terminal state."""

    async def approval(state: WorkflowState) -> WorkflowState:
        await snapshot_package(deps.session, deps.run_id, state)
        await request_approval(deps.session, deps.run_id)
        state.status = "awaiting_approval"
        return state

    return approval
