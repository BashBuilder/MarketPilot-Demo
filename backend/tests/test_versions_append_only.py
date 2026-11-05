"""Prove that a persisted campaign version can never be rewritten or deleted."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.database.models import Base, CampaignVersion, ImmutableVersionError
from app.database.repositories import campaigns, versions


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


async def _seed_two_versions(
    session: AsyncSession,
) -> tuple[UUID, UUID, int]:
    campaign = await campaigns.create(session, idea="Append-only test")
    first = await versions.create(
        session,
        campaign_id=campaign.id,
        package={"brief": {"goal": "awareness"}},
    )
    second = await versions.create(
        session,
        campaign_id=campaign.id,
        package={"brief": {"goal": "launch"}},
        parent_version_id=first.id,
    )
    await session.commit()
    return campaign.id, first.id, second.version


async def test_previous_version_cannot_be_updated(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        campaign_id, first_id, second_version = await _seed_two_versions(session)
        first = await session.get(CampaignVersion, first_id)
        assert first is not None

        first.package = {"brief": {"goal": "rewritten"}}
        with pytest.raises(ImmutableVersionError):
            await session.flush()
        await session.rollback()

        stored = await versions.get(session, campaign_id, 1)
        assert stored is not None
        assert stored.package == {"brief": {"goal": "awareness"}}
        assert stored.version == 1
        assert second_version == 2


async def test_previous_version_cannot_be_deleted(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        campaign_id, first_id, _ = await _seed_two_versions(session)
        first = await session.get(CampaignVersion, first_id)
        assert first is not None

        await session.delete(first)
        with pytest.raises(ImmutableVersionError):
            await session.flush()
        await session.rollback()

        assert await versions.get(session, campaign_id, 1) is not None
