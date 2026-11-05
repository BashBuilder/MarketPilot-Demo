"""Supervised loop behavior against real PostgreSQL with scripted agents."""

from uuid import UUID

import pytest
from node_fakes import RecordingEmitter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_loop_fakes import (
    COPY,
    FAIL_COPY_REPORT,
    IDEA,
    PASS_REPORT,
    REVISED_COPY,
    ScriptedAgent,
    default_agents,
    score,
)

from app.agents.supervisor import AUTO_LOOP_KEY
from app.core.config import Settings
from app.core.errors import RetryExhausted
from app.database.repositories import campaigns, runs
from app.graph.state import WorkflowState
from app.graph.workflow import WorkflowDependencies, build_workflow
from app.harness.checkpoints import load_latest_checkpoint

pytestmark = pytest.mark.postgres


async def _run(
    factory: async_sessionmaker[AsyncSession],
    agents: dict[str, ScriptedAgent],
    *,
    max_auto_loops: int = 2,
) -> tuple[UUID, WorkflowState]:
    config = Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        redis_url="redis://localhost:6379/0",
        max_auto_loops=max_auto_loops,
        score_threshold=70,
        retry_max_attempts=1,
    )
    async with factory() as session:
        campaign = await campaigns.create(session, idea=IDEA)
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        run_id = run.id
        graph = build_workflow(
            agents,
            WorkflowDependencies(
                run_id=run_id,
                llm=object(),
                session=session,
                emit=RecordingEmitter(),
                tools={},
                settings=config,
            ),
        )
        raw = await graph.ainvoke({"idea": IDEA})
        await session.commit()
    return run_id, WorkflowState.model_validate(raw)


async def _counter(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> int:
    async with factory() as session:
        loaded = await load_latest_checkpoint(session, run_id)
    assert loaded is not None
    return loaded.retry_counters.get(AUTO_LOOP_KEY, 0)


async def test_copy_failure_loops_to_copywriter_once(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    agents = default_agents()
    agents["copywriter"] = ScriptedAgent("copywriter", [COPY, REVISED_COPY])
    agents["compliance"] = ScriptedAgent("compliance", [FAIL_COPY_REPORT, PASS_REPORT])

    _, final = await _run(pg_session_factory, agents)

    assert agents["copywriter"].calls == 2
    assert agents["compliance"].calls == 2
    assert final.compliance == PASS_REPORT
    assert final.status == "awaiting_approval"


async def test_low_score_loops_to_the_weakest_node(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    agents = default_agents()
    agents["reviewer"] = ScriptedAgent("reviewer", [score(2), score(9)])

    _, final = await _run(pg_session_factory, agents)

    assert agents["copywriter"].calls == 2
    assert agents["reviewer"].calls == 2
    assert final.score == score(9)
    assert final.status == "awaiting_approval"


async def test_third_low_score_stops_at_the_human_gate(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    agents = default_agents()
    agents["reviewer"] = ScriptedAgent("reviewer", [score(2), score(2), score(2)])

    run_id, final = await _run(pg_session_factory, agents)

    assert agents["copywriter"].calls == 3
    assert agents["reviewer"].calls == 3
    assert await _counter(pg_session_factory, run_id) == 2
    assert final.status == "awaiting_approval"


async def test_retry_exhausted_escalates_without_running_the_reviewer(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    agents = default_agents()
    agents["compliance"] = ScriptedAgent(
        "compliance",
        error=RetryExhausted("compliance output failed verification"),
    )

    _, final = await _run(pg_session_factory, agents)

    assert agents["reviewer"].calls == 0
    assert any("compliance" in error for error in final.errors)
    assert final.status == "awaiting_approval"


async def test_retry_exhausted_at_brief_skips_downstream_agents(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    agents = default_agents()
    agents["brief"] = ScriptedAgent("brief", error=RetryExhausted("brief failed"))

    _, final = await _run(pg_session_factory, agents)

    assert agents["research"].calls == 0
    assert agents["reviewer"].calls == 0
    assert any("brief" in error for error in final.errors)
    assert final.status == "awaiting_approval"


async def test_loop_counter_survives_a_checkpoint_reload(
    pg_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    agents = default_agents()
    agents["reviewer"] = ScriptedAgent("reviewer", [score(2), score(9)])

    run_id, _ = await _run(pg_session_factory, agents)

    async with pg_session_factory() as session:
        loaded = await load_latest_checkpoint(session, run_id)

    assert loaded is not None
    assert loaded.retry_counters[AUTO_LOOP_KEY] == 1
