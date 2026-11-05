"""Tests for the async session context manager."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Base, Campaign
from app.database.session import session_scope


@pytest.fixture()
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def test_scope_commits_on_success(engine: AsyncEngine) -> None:
    async with session_scope(engine) as session:
        session.add(Campaign(idea="committed idea"))

    async with session_scope(engine) as session:
        count = await session.scalar(select(func.count()).select_from(Campaign))

    assert count == 1


async def test_scope_rolls_back_and_propagates(engine: AsyncEngine) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        async with session_scope(engine) as session:
            session.add(Campaign(idea="rolled back idea"))
            await session.flush()
            raise RuntimeError("boom")

    async with session_scope(engine) as session:
        count = await session.scalar(select(func.count()).select_from(Campaign))

    assert count == 0


async def test_scope_opens_a_fresh_session_each_time(engine: AsyncEngine) -> None:
    async with session_scope(engine) as first:
        pass
    async with session_scope(engine) as second:
        pass

    assert first is not second
