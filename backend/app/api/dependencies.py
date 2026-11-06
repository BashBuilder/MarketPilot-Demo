"""Request-scoped dependencies and the run launcher boundary."""

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Protocol, cast
from uuid import UUID

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.contracts import ChatMessage, LLMClient, ToolInvoker
from app.core.config import Settings, get_settings
from app.database.session import session_scope
from app.events.bus import EventBus, InMemoryEventBus
from app.events.emitter import make_emitter
from app.graph.node_support import NodeEventEmitter
from app.graph.nodes import NodeAgent
from app.graph.workflow import WorkflowDependencies
from app.harness.registry import AgentName, ToolRegistry
from app.runs.services import build_tools


class RunLauncher(Protocol):
    """Starts a workflow run after its database row has been committed."""

    async def start(self, run_id: UUID) -> None: ...


@dataclass(slots=True)
class RecordingRunLauncher:
    """Temporary launcher that records ids until the graph runner is wired in."""

    started: list[UUID] = field(default_factory=list)

    async def start(self, run_id: UUID) -> None:
        self.started.append(run_id)


@dataclass(frozen=True, slots=True)
class WorkflowServices:
    """Process-wide collaborators the approval operations need."""

    agents: Mapping[AgentName, NodeAgent]
    llm: LLMClient
    tools: Mapping[AgentName, ToolInvoker]
    emit: NodeEventEmitter
    registry: ToolRegistry | None = None
    session_factory: async_sessionmaker[AsyncSession] | None = None


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """One request's workflow dependencies plus the services behind them."""

    services: WorkflowServices
    deps: WorkflowDependencies


class _UnavailableLLM:
    async def structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[BaseModel],
    ) -> Any:
        del messages, schema
        raise RuntimeError("no LLM client is configured for API requests")


DEFAULT_EVENT_BUS: EventBus = InMemoryEventBus()

DEFAULT_WORKFLOW_SERVICES = WorkflowServices(
    agents={},
    llm=_UnavailableLLM(),
    tools={},
    emit=make_emitter(DEFAULT_EVENT_BUS),
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Open one committed-or-rolled-back session per request."""
    async with session_scope() as session:
        yield session


def get_run_launcher(request: Request) -> RunLauncher:
    """Return the launcher configured on the application."""
    launcher = getattr(request.app.state, "run_launcher", None)
    if launcher is None:
        raise RuntimeError("run launcher is not configured")
    return cast(RunLauncher, launcher)


def get_workflow_services(request: Request) -> WorkflowServices:
    """Return the process-wide workflow collaborators."""
    services = getattr(request.app.state, "workflow_services", None)
    if services is None:
        raise RuntimeError("workflow services are not configured")
    return cast(WorkflowServices, services)


def get_event_bus(request: Request) -> EventBus:
    """Return the process-wide event bus used for replay and live streams."""
    bus = getattr(request.app.state, "event_bus", None)
    if bus is None:
        raise RuntimeError("event bus is not configured")
    return cast(EventBus, bus)


def get_workflow_context(
    run_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    services: Annotated[WorkflowServices, Depends(get_workflow_services)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkflowContext:
    """Bind the request session and run id to the shared services."""
    tools = services.tools
    if services.registry is not None and services.session_factory is not None:
        tools = build_tools(
            registry=services.registry,
            settings=settings,
            session_factory=services.session_factory,
            run_id=run_id,
        )
    deps = WorkflowDependencies(
        run_id=run_id,
        llm=services.llm,
        session=session,
        emit=services.emit,
        tools=tools,
        settings=settings,
    )
    return WorkflowContext(services=services, deps=deps)
