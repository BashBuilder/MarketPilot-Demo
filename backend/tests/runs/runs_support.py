"""Fakes and builders shared by the startup recovery tests."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.database.models import RunStatus
from app.database.repositories import campaigns, checkpoints, runs


class FakeLauncher:
    """Record attempted resumes and fail the ids the test names."""

    def __init__(self, fail_on: set[UUID] | None = None) -> None:
        self.fail_on = fail_on or set()
        self.attempts: list[UUID] = []
        self.started: list[UUID] = []

    async def start(self, run_id: UUID) -> None:
        self.attempts.append(run_id)
        if run_id in self.fail_on:
            raise RuntimeError("launcher failed")
        self.started.append(run_id)


class FakeLock:
    def __init__(self, acquired: bool) -> None:
        self.acquired = acquired
        self.released = False

    async def acquire(self, blocking: bool = False) -> bool:
        del blocking
        return self.acquired

    async def release(self) -> None:
        self.released = True


class FakeRedis:
    """Return a scripted lock for each run key."""

    def __init__(self, locked: set[UUID] | None = None) -> None:
        self.locked = locked or set()
        self.locks: list[FakeLock] = []

    def lock(self, name: str, *, timeout: int, blocking_timeout: int = 0) -> FakeLock:
        del timeout, blocking_timeout
        run_id = UUID(name.removeprefix("run:").removesuffix(":resume"))
        lock = FakeLock(run_id not in self.locked)
        self.locks.append(lock)
        return lock


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "deepseek_api_key": "test-key",
        "database_url": "sqlite+aiosqlite://",
        "redis_url": "redis://localhost:6379/0",
        "resume_on_startup": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


async def make_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    status: RunStatus = RunStatus.RUNNING,
    state: dict[str, Any] | None = None,
) -> UUID:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Startup resume test")
        run = await runs.create(session, campaign_id=campaign.id)
        await runs.set_status(session, run.id, status, current_node="brief")
        if state is not None:
            await checkpoints.create(session, run_id=run.id, node="brief", state=state)
        await session.commit()
        return run.id
