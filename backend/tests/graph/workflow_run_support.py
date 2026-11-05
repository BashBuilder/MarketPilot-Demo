"""Shared setup for workflow run, resume and decision integration tests."""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_loop_fakes import IDEA, ScriptedAgent

from app.core.config import Settings
from app.database.repositories import campaigns, checkpoints, runs, versions
from app.graph.node_support import NodeEventEmitter
from app.graph.state import WorkflowState
from app.graph.workflow import WorkflowDependencies
from app.harness.checkpoints import load_latest_checkpoint


def run_settings() -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        redis_url="redis://localhost:6379/0",
        max_auto_loops=2,
        score_threshold=70,
        retry_max_attempts=1,
    )


async def new_run(factory: async_sessionmaker[AsyncSession]) -> tuple[UUID, UUID]:
    """Create a campaign and its first run, returning both ids."""
    async with factory() as session:
        campaign = await campaigns.create(session, idea=IDEA)
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id, campaign.id


async def add_version(
    factory: async_sessionmaker[AsyncSession],
    campaign_id: UUID,
    *,
    score: float = 82.0,
) -> None:
    """Human decisions need a version to attach the audit entry to."""
    async with factory() as session:
        await versions.create(
            session,
            campaign_id=campaign_id,
            package={"brief": {}},
            score=score,
        )
        await session.commit()


def dependencies(
    run_id: UUID,
    session: AsyncSession,
    emit: NodeEventEmitter,
    settings: Settings,
) -> WorkflowDependencies:
    return WorkflowDependencies(
        run_id=run_id,
        llm=object(),
        session=session,
        emit=emit,
        tools={},
        settings=settings,
    )


async def latest_state(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> WorkflowState:
    async with factory() as session:
        state = await load_latest_checkpoint(session, run_id)
    assert state is not None
    return state


async def checkpoint_nodes(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> list[str]:
    async with factory() as session:
        rows = await checkpoints.list_for_run(session, run_id)
    return [row.node for row in rows]


def reset_calls(agents: Mapping[str, ScriptedAgent]) -> None:
    for agent in agents.values():
        agent.calls = 0
