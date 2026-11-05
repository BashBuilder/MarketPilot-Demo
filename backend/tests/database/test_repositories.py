"""Tests for the campaign, run, version and approval repositories."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.database.models import ApprovalDecision, Base, CampaignStatus, RunStatus
from app.database.repositories import approvals, campaigns, runs, versions


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


async def test_campaign_repository_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="A fictional hair-care campaign")
        assert campaign.status is CampaignStatus.DRAFT

        fetched = await campaigns.get(session, campaign.id)
        assert fetched is not None
        assert fetched.id == campaign.id

        updated = await campaigns.set_status(session, campaign.id, CampaignStatus.RUNNING)
        assert updated is not None
        assert updated.status is CampaignStatus.RUNNING
        assert await campaigns.set_status(session, uuid4(), CampaignStatus.RUNNING) is None

        listed = await campaigns.list_all(session)
        assert [item.id for item in listed] == [campaign.id]


async def test_run_repository_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Run test")
        run = await runs.create(session, campaign_id=campaign.id)
        assert run.status is RunStatus.PENDING

        updated = await runs.set_status(session, run.id, RunStatus.RUNNING, current_node="brief")
        assert updated is not None
        assert updated.status is RunStatus.RUNNING
        assert updated.current_node == "brief"

        listed = await runs.list_for_campaign(session, campaign.id)
        assert [item.id for item in listed] == [run.id]

        cleared = await runs.set_status(session, run.id, RunStatus.COMPLETED)
        assert cleared is not None
        assert cleared.current_node is None


async def test_version_repository_numbers_versions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Version test")
        first = await versions.create(session, campaign_id=campaign.id, package={"n": 1})
        second = await versions.create(
            session,
            campaign_id=campaign.id,
            package={"n": 2},
            parent_version_id=first.id,
            score=82.0,
        )

        assert (first.version, second.version) == (1, 2)
        assert second.parent_version_id == first.id

        latest = await versions.get_latest(session, campaign.id)
        assert latest is not None
        assert latest.id == second.id

        stored_first = await versions.get(session, campaign.id, 1)
        assert stored_first is not None
        assert stored_first.id == first.id

        listed = await versions.list_for_campaign(session, campaign.id)
        assert [item.version for item in listed] == [1, 2]


async def test_approval_repository_records_decisions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Approval test")
        run = await runs.create(session, campaign_id=campaign.id)
        version = await versions.create(session, campaign_id=campaign.id, package={"n": 1})

        approval = await approvals.create(
            session,
            run_id=run.id,
            campaign_version_id=version.id,
            decision=ApprovalDecision.REVISE,
            comment="Tighten the claims",
            target_node="copywriter",
        )
        assert approval.decision is ApprovalDecision.REVISE

        latest = await approvals.get_latest_for_run(session, run.id)
        assert latest is not None
        assert latest.id == approval.id

        listed = await approvals.list_for_run(session, run.id)
        assert [item.id for item in listed] == [approval.id]
