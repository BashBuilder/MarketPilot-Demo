"""Event bus wiring: node handoffs, tool calls and verification retries."""

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from node_fakes import VALID_BRIEF
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_loop_fakes import IDEA, RESEARCH, ScriptedAgent, default_agents
from workflow_run_support import dependencies, run_settings

from app.agents.outputs import CampaignBrief
from app.events.bus import InMemoryEventBus
from app.events.emitter import make_emitter
from app.graph.node_support import verification_event_emitter
from app.graph.routing import PIPELINE
from app.graph.workflow import build_workflow
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import ToolRegistry, ToolSpec
from app.harness.verification import run_with_verification


class EchoArgs(BaseModel):
    text: str


async def echo(args: EchoArgs) -> str:
    return args.text


class ToolCallingAgent(ScriptedAgent):
    """Scripted agent that exercises the tool middleware before returning."""

    def __init__(self, name: str, outputs: list[Any], tool: str) -> None:
        super().__init__(name, outputs)
        self.tool = tool

    async def run(
        self,
        state: Any,
        llm: object,
        emit: object = None,
        tools: object = None,
        *,
        settings: object = None,
    ) -> Any:
        assert tools is not None
        await tools.call(self.tool, {"text": "research"})  # type: ignore[attr-defined]
        return await super().run(state, llm, emit, tools, settings=settings)


async def test_full_run_events_follow_pipeline_order_with_tool_calls(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> None:
    bus = InMemoryEventBus()
    settings = run_settings()
    registry = ToolRegistry()
    registry.register_tool(ToolSpec(name="search_tools", args_model=EchoArgs, run=echo))
    middleware = ToolCallMiddleware(
        registry=registry,
        guardrails=RunGuardrails(settings),
        session_factory=session_factory,
        run_id=run_id,
        agent="research",
    )
    agents = default_agents()
    agents["research"] = ToolCallingAgent("research", [RESEARCH], "search_tools")

    async with session_factory() as session:
        deps = replace(
            dependencies(run_id, session, make_emitter(bus), settings),
            tools={"research": middleware},
        )
        await build_workflow(agents, deps).ainvoke({"idea": IDEA})
        await session.commit()

    records = await bus.read(run_id, None)
    expected: list[str] = []
    for name in PIPELINE:
        expected.append("agent_started")
        if name == "research":
            expected.append("tool_called")
        expected.append("agent_handoff")
    expected.append("awaiting_approval")

    assert [record.event for record in records] == expected
    assert all(
        record.data["run_id"] == str(run_id) and record.data["timestamp"] and record.data["agent"]
        for record in records
    )
    tool_event = next(record for record in records if record.event == "tool_called")
    assert tool_event.data["tool"] == "search_tools"
    assert tool_event.data["status"] == "success"
    assert isinstance(tool_event.data["duration_ms"], int)


async def test_validation_failure_publishes_failure_then_retry() -> None:
    bus = InMemoryEventBus()
    run_id = uuid4()
    relay = verification_event_emitter(make_emitter(bus), run_id=run_id, agent="brief")
    settings = run_settings().model_copy(update={"retry_max_attempts": 2})
    attempts = 0

    async def step(_feedback: str) -> Any:
        nonlocal attempts
        attempts += 1
        return {} if attempts == 1 else VALID_BRIEF.model_dump(mode="json")

    async def no_sleep(_delay: float) -> None:
        return None

    result = await run_with_verification(
        step,
        model=CampaignBrief,
        on_event=relay,
        settings=settings,
        sleep=no_sleep,
        jitter=lambda: 0.0,
    )

    assert result == VALID_BRIEF
    records = await bus.read(run_id, None)
    assert [record.event for record in records] == ["validation_failed", "retrying"]
    assert records[0].data["attempt"] == 1
    assert records[0].data["issues"]
    assert records[1].data["delay"] is not None
