"""Node wrappers that run a single agent through the harness.

Persistence belongs here, not in agents: a node validates the output, writes
the immutable ``agent_outputs`` row, and checkpoints the merged state before
announcing the handoff. A handoff is only emitted once all three are done.
"""

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import EventEmitter, LLMClient, ToolInvoker
from app.core.config import Settings
from app.core.errors import RetryExhausted
from app.database.repositories import agent_outputs
from app.graph.node_support import (
    NodeEventEmitter,
    event_payload,
    handoff_target,
    merge_output,
    verification_event_emitter,
)
from app.graph.state import WorkflowState
from app.harness.checkpoints import save_checkpoint
from app.harness.context import build_agent_context
from app.harness.registry import AgentName


class WorkflowNode(Protocol):
    """A LangGraph-compatible async node over the shared workflow state."""

    def __call__(self, state: WorkflowState) -> Awaitable[WorkflowState]: ...


class NodeAgent(Protocol):
    """The part of an agent a node depends on; tests can fake it cheaply."""

    name: AgentName
    context_budget: int

    async def run(
        self,
        state: WorkflowState,
        llm: LLMClient,
        emit: EventEmitter | None = None,
        tools: ToolInvoker | None = None,
        *,
        settings: Settings | None = None,
    ) -> BaseModel: ...


@dataclass(frozen=True, slots=True)
class NodeDependencies:
    """Per-run dependencies injected so nodes stay free of global state."""

    run_id: UUID
    llm: LLMClient
    session: AsyncSession
    emit: NodeEventEmitter
    tools: ToolInvoker | None = None
    settings: Settings | None = None


def make_node(agent: NodeAgent, deps: NodeDependencies) -> WorkflowNode:
    """Build the async node for ``agent`` with its run-scoped dependencies."""

    async def node(state: WorkflowState) -> WorkflowState:
        await deps.emit("agent_started", event_payload(deps.run_id, agent.name))
        context = build_agent_context(state, agent.name, agent.context_budget)
        relay = verification_event_emitter(deps.emit, run_id=deps.run_id, agent=agent.name)
        try:
            output = await agent.run(
                context,
                deps.llm,
                emit=relay,
                tools=deps.tools,
                settings=deps.settings,
            )
        except RetryExhausted as exc:
            return await _escalate(state, agent.name, exc, deps)

        merge_output(state, agent.name, output)
        await agent_outputs.create(
            deps.session,
            run_id=deps.run_id,
            agent=agent.name,
            output=output.model_dump(mode="json"),
        )
        await save_checkpoint(deps.session, deps.run_id, agent.name, state)

        handoff = event_payload(deps.run_id, agent.name)
        handoff.update({"from": agent.name, "to": handoff_target(agent.name, output)})
        await deps.emit("agent_handoff", handoff)
        return state

    return node


async def _escalate(
    state: WorkflowState,
    agent: AgentName,
    exc: RetryExhausted,
    deps: NodeDependencies,
) -> WorkflowState:
    """Stop retrying, persist the escalation, and tell the human why."""
    state.status = "escalated"
    state.errors.append(f"{agent}: {exc.message}")
    await save_checkpoint(deps.session, deps.run_id, agent, state)
    error = event_payload(deps.run_id, agent)
    error.update({"message": exc.message, "recoverable": False})
    await deps.emit("error", error)
    return state
