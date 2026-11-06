"""Startup recovery: claim running runs, isolate failures and respect the switch."""

from collections.abc import AsyncIterator

import pytest
from runs_support import FakeLauncher, FakeRedis, make_run, make_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Base, RunStatus
from app.graph.state import WorkflowState
from app.runs.startup import resume_unfinished_runs


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_running_run_is_resumed_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await make_run(session_factory)
    launcher = FakeLauncher()
    redis = FakeRedis()

    resumed = await resume_unfinished_runs(
        session_factory=session_factory,
        launcher=launcher,
        settings=make_settings(),
        redis=redis,  # type: ignore[arg-type]
    )

    assert resumed == [run_id]
    assert launcher.attempts == [run_id]
    assert redis.locks[0].released is True


async def test_locked_run_is_skipped(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await make_run(session_factory)
    launcher = FakeLauncher()

    resumed = await resume_unfinished_runs(
        session_factory=session_factory,
        launcher=launcher,
        settings=make_settings(),
        redis=FakeRedis(locked={run_id}),  # type: ignore[arg-type]
    )

    assert resumed == []
    assert launcher.attempts == []


async def test_one_failed_resume_does_not_block_the_rest(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = await make_run(session_factory)
    second = await make_run(session_factory)
    launcher = FakeLauncher(fail_on={first})

    resumed = await resume_unfinished_runs(
        session_factory=session_factory,
        launcher=launcher,
        settings=make_settings(),
        redis=FakeRedis(),  # type: ignore[arg-type]
    )

    assert set(launcher.attempts) == {first, second}
    assert launcher.started == [second]
    assert resumed == [second]


async def test_disabled_switch_resumes_nothing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await make_run(session_factory)
    launcher = FakeLauncher()
    redis = FakeRedis()

    resumed = await resume_unfinished_runs(
        session_factory=session_factory,
        launcher=launcher,
        settings=make_settings(resume_on_startup=False),
        redis=redis,  # type: ignore[arg-type]
    )

    assert resumed == []
    assert launcher.attempts == []
    assert redis.locks == []


@pytest.mark.parametrize(
    "status",
    [RunStatus.PENDING, RunStatus.AWAITING_APPROVAL, RunStatus.COMPLETED, RunStatus.FAILED],
)
async def test_non_running_statuses_are_skipped(
    session_factory: async_sessionmaker[AsyncSession],
    status: RunStatus,
) -> None:
    await make_run(session_factory, status=status)
    launcher = FakeLauncher()

    resumed = await resume_unfinished_runs(
        session_factory=session_factory,
        launcher=launcher,
        settings=make_settings(),
        redis=FakeRedis(),  # type: ignore[arg-type]
    )

    assert resumed == []
    assert launcher.attempts == []


async def test_escalated_checkpoint_is_skipped(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await make_run(
        session_factory,
        state=WorkflowState(idea="Startup resume test", status="escalated").model_dump(mode="json"),
    )
    launcher = FakeLauncher()

    resumed = await resume_unfinished_runs(
        session_factory=session_factory,
        launcher=launcher,
        settings=make_settings(),
        redis=FakeRedis(),  # type: ignore[arg-type]
    )

    assert resumed == []
    assert launcher.attempts == []
