"""Background launcher that drives a run through the compiled graph.

``start`` returns as soon as the task is scheduled so campaign creation stays
fast; the stream endpoint delivers progress from the event bus. A run that
raises unexpectedly is marked failed and emits a terminal error event, which is
what lets the frontend leave its connecting state.
"""

import asyncio
import logging
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.contracts import LLMClient
from app.core.config import Settings
from app.core.errors import MarketPilotError
from app.core.logging import bind_run_context
from app.database.models import CampaignStatus, RunStatus
from app.database.repositories import campaigns, runs
from app.events.bus import EventBus
from app.events.emitter import make_emitter
from app.graph.node_support import NodeEventEmitter, event_payload
from app.graph.nodes import NodeAgent
from app.graph.workflow import WorkflowDependencies, run_workflow
from app.harness.registry import AgentName, ToolRegistry
from app.runs.services import build_tools

logger = logging.getLogger(__name__)

_UNEXPECTED_FAILURE = "The run failed unexpectedly. Check the server logs for details."


class WorkflowRunLauncher:
    """Start runs in background tasks and guarantee a terminal stream event."""

    def __init__(
        self,
        *,
        agents: Mapping[AgentName, NodeAgent],
        llm: LLMClient,
        registry: ToolRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
        settings: Settings,
    ) -> None:
        self._agents = agents
        self._llm = llm
        self._registry = registry
        self._session_factory = session_factory
        self._emit = make_emitter(event_bus)
        self._settings = settings
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self, run_id: UUID) -> None:
        """Schedule one run without blocking the request that created it."""
        task = asyncio.create_task(self._run(run_id), name=f"workflow-run-{run_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait(self) -> None:
        """Wait for every run scheduled so far; used by tests and shutdown."""
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def close(self) -> None:
        """Cancel in-flight runs during shutdown before the event bus closes."""
        for task in list(self._tasks):
            task.cancel()
        await self.wait()

    async def _run(self, run_id: UUID) -> None:
        with bind_run_context(run_id=str(run_id)):
            try:
                async with self._session_factory() as session:
                    deps = WorkflowDependencies(
                        run_id=run_id,
                        llm=self._llm,
                        session=session,
                        emit=self._emit,
                        tools=build_tools(
                            registry=self._registry,
                            settings=self._settings,
                            session_factory=self._session_factory,
                            run_id=run_id,
                        ),
                        settings=self._settings,
                    )
                    await run_workflow(run_id, agents=self._agents, deps=deps)
                    await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("run failed", extra={"run_id": str(run_id)})
                await self._fail(run_id, exc)

    async def _fail(self, run_id: UUID, exc: Exception) -> None:
        """Persist the failure before announcing it, mirroring node escalation."""
        message = exc.message if isinstance(exc, MarketPilotError) else _UNEXPECTED_FAILURE
        try:
            async with self._session_factory() as session:
                failed = await runs.set_status(
                    session,
                    run_id,
                    RunStatus.FAILED,
                    current_node=None,
                    error=message,
                )
                if failed is not None:
                    await campaigns.set_status(session, failed.campaign_id, CampaignStatus.FAILED)
                await session.commit()
        except Exception:
            logger.exception("could not record failed run", extra={"run_id": str(run_id)})

        await self._publish_error(run_id, message)

    async def _publish_error(self, run_id: UUID, message: str) -> None:
        emitter: NodeEventEmitter = self._emit
        data = event_payload(run_id, "supervisor")
        data.update({"message": message, "recoverable": False})
        try:
            await emitter("error", data)
        except Exception:
            logger.exception("could not publish run failure", extra={"run_id": str(run_id)})
