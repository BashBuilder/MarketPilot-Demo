"""Compliance routing must stop looping once the automatic-loop budget is spent."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from node_fakes import RecordingEmitter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_loop_fakes import FAIL_COPY_REPORT, IDEA, ScriptedAgent, default_agents

from app.agents.outputs import ComplianceItem, ComplianceReport
from app.agents.supervisor import AUTO_LOOP_KEY
from app.core.config import Settings
from app.database.repositories import campaigns, runs
from app.graph.routing import APPROVAL_NODE, make_compliance_router
from app.graph.state import WorkflowState
from app.graph.workflow import WorkflowDependencies, build_workflow

COPY_FAILURE = ComplianceReport(
    items=[
        ComplianceItem(
            check="variant 2 (Email): guaranteed results",
            passed=False,
            reason="Remove the guarantee.",
        )
    ]
)


def settings(max_auto_loops: int = 2) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        redis_url="redis://localhost:6379/0",
        max_auto_loops=max_auto_loops,
        score_threshold=70,
        retry_max_attempts=1,
    )


def state(*, loops: int = 0) -> WorkflowState:
    return WorkflowState(
        idea=IDEA,
        compliance=COPY_FAILURE,
        retry_counters={AUTO_LOOP_KEY: loops},
    )


def test_compliance_failure_enters_the_loop_node() -> None:
    decision = make_compliance_router(settings())(state())

    assert decision == "loop_copywriter"


def test_compliance_failure_escalates_when_the_budget_is_spent() -> None:
    decision = make_compliance_router(settings(max_auto_loops=2))(state(loops=2))

    assert decision == APPROVAL_NODE


@pytest.fixture()
async def sqlite_run(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[UUID]:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea=IDEA)
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        yield run.id


async def test_persistent_compliance_failure_stops_at_the_human_gate(
    session_factory: async_sessionmaker[AsyncSession],
    sqlite_run: UUID,
) -> None:
    agents = default_agents()
    agents["compliance"] = ScriptedAgent("compliance", [FAIL_COPY_REPORT])

    async with session_factory() as session:
        graph = build_workflow(
            agents,
            WorkflowDependencies(
                run_id=sqlite_run,
                llm=object(),
                session=session,
                emit=RecordingEmitter(),
                tools={},
                settings=settings(),
            ),
        )
        raw = await graph.ainvoke({"idea": IDEA})
        await session.commit()

    final = WorkflowState.model_validate(raw)
    assert agents["copywriter"].calls == 3
    assert final.retry_counters[AUTO_LOOP_KEY] == 2
    assert final.status == "awaiting_approval"
