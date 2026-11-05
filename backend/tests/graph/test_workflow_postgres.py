"""Real-Postgres happy path for the linear seven-agent workflow."""

from pathlib import Path

import pytest
from node_fakes import RecordingEmitter, event_names
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_fakes import IDEA, PAYLOADS, FakeWorkflowLLM

from app.agents.brief import BriefAgent
from app.agents.compliance import ComplianceAgent
from app.agents.copywriter import CopywriterAgent
from app.agents.creative_director import CreativeDirectorAgent
from app.agents.designer import DesignerAgent
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.core.config import Settings
from app.database.models import RunStatus, ToolCall
from app.database.repositories import agent_outputs, campaigns, checkpoints, runs
from app.database.seed import seed
from app.graph.state import WorkflowState
from app.graph.workflow import PIPELINE, WorkflowDependencies, build_workflow
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import ToolRegistry
from app.llm.embeddings import FakeEmbedder
from app.tools.image_tools import FakeImageGenerator, register_image_tools
from app.tools.policy_tools import register_policy_tools
from app.tools.search_tools import FakeSearchProvider, register_search_tools

pytestmark = pytest.mark.postgres

AGENTS = {
    "brief": BriefAgent(),
    "research": ResearchAgent(),
    "copywriter": CopywriterAgent(),
    "creative_director": CreativeDirectorAgent(),
    "designer": DesignerAgent(),
    "compliance": ComplianceAgent(),
    "reviewer": ReviewerAgent(),
}

EXPECTED_TARGETS = [
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "human",
]


def limits(asset_dir: Path) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        redis_url="redis://localhost:6379/0",
        asset_dir=asset_dir,
        retry_max_attempts=1,
    )


async def test_linear_workflow_persists_outputs_checkpoints_and_events(
    pg_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    config = limits(tmp_path)
    async with pg_session_factory() as session:
        campaign = await campaigns.create(session, idea=IDEA)
        run = await runs.create(session, campaign_id=campaign.id)
        await seed(session, FakeEmbedder())
        await session.commit()
        run_id = run.id

    registry = ToolRegistry()
    register_search_tools(registry, FakeSearchProvider())
    register_image_tools(registry, FakeImageGenerator(tmp_path))
    register_policy_tools(registry, session_factory=pg_session_factory, embedder=FakeEmbedder())
    guardrails = RunGuardrails(config)
    tools = {
        name: ToolCallMiddleware(
            registry=registry,
            guardrails=guardrails,
            session_factory=pg_session_factory,
            run_id=run_id,
            agent=name,
        )
        for name in PIPELINE
    }
    emitter = RecordingEmitter()
    llm = FakeWorkflowLLM()

    async with pg_session_factory() as session:
        graph = build_workflow(
            AGENTS,
            WorkflowDependencies(
                run_id=run_id,
                llm=llm,
                session=session,
                emit=emitter,
                tools=tools,
                settings=config,
            ),
        )
        raw = await graph.ainvoke({"idea": IDEA})
        await session.commit()

    final = WorkflowState.model_validate(raw)
    assert final.status == "awaiting_approval"
    assert all(
        getattr(final, field) is not None
        for field in ("brief", "research", "copy", "direction", "assets", "compliance", "score")
    )

    async with pg_session_factory() as session:
        outputs = await agent_outputs.list_for_run(session, run_id)
        saved = await checkpoints.list_for_run(session, run_id)
        stored_run = await runs.get(session, run_id)
        tool_rows = list(
            (
                await session.scalars(
                    select(ToolCall)
                    .where(ToolCall.run_id == run_id)
                    .order_by(ToolCall.created_at.asc())
                )
            ).all()
        )

    assert [row.agent for row in outputs] == list(PIPELINE)
    assert [row.node for row in saved] == [*PIPELINE, "human"]
    assert [row.step for row in saved] == list(range(1, len(PIPELINE) + 2))
    assert stored_run is not None
    assert stored_run.status is RunStatus.AWAITING_APPROVAL
    assert stored_run.current_node == "human"

    expected_events = [event for _ in PIPELINE for event in ("agent_started", "agent_handoff")]
    expected_events.append("awaiting_approval")
    assert event_names(emitter) == expected_events
    handoffs = [data for name, data in emitter.events if name == "agent_handoff"]
    assert [data["from"] for data in handoffs] == list(PIPELINE)
    assert [data["to"] for data in handoffs] == EXPECTED_TARGETS

    assert [row.tool for row in tool_rows] == [
        "search_tools",
        "policy_lookup",
        "generate_image",
        "policy_lookup",
        "policy_lookup",
    ]
    assert all(row.status == "success" for row in tool_rows)
    assert llm.calls == len(PAYLOADS)
