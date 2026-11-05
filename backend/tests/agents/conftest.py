"""SQLite schema and workflow run for agent tests that audit tool calls."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.database.repositories import campaigns, runs


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


@pytest.fixture()
async def run_id(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Research agent test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id
