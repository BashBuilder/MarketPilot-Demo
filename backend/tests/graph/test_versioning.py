"""Append-only campaign version snapshots taken at the human gate."""

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.outputs import AdCopySet
from app.database.models import CampaignVersion, ImmutableVersionError
from app.database.repositories import assets, campaigns, runs, versions
from app.graph.state import WorkflowState
from app.graph.versioning import PACKAGE_FIELDS, snapshot_package

REVISED_COPY = AdCopySet(
    variants=[
        {
            "channel": "Instagram",
            "headline": "A gentler ritual",
            "description": "Care for colour-treated hair without guarantees.",
            "cta": "See the routine",
        }
    ]
)


async def _run(factory: async_sessionmaker[AsyncSession]) -> tuple[UUID, UUID]:
    async with factory() as session:
        campaign = await campaigns.create(session, idea="Versioning test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id, campaign.id


def _row(version: CampaignVersion) -> dict[str, object]:
    return {
        "id": version.id,
        "campaign_id": version.campaign_id,
        "version": version.version,
        "parent_version_id": version.parent_version_id,
        "package": version.package,
        "score": version.score,
        "created_at": version.created_at,
    }


async def test_first_snapshot_creates_version_one_without_a_parent(
    session_factory: async_sessionmaker[AsyncSession],
    full_state: WorkflowState,
) -> None:
    run_id, campaign_id = await _run(session_factory)

    async with session_factory() as session:
        version = await snapshot_package(session, run_id, full_state)
        await session.commit()

        assert version.version == 1
        assert version.parent_version_id is None
        assert set(version.package) == set(PACKAGE_FIELDS)
        stored = await versions.get(session, campaign_id, 1)

    assert stored is not None
    assert stored.score == 76.0


async def test_snapshot_persists_the_asset_rows_for_the_version(
    session_factory: async_sessionmaker[AsyncSession],
    full_state: WorkflowState,
) -> None:
    run_id, _ = await _run(session_factory)

    async with session_factory() as session:
        version = await snapshot_package(session, run_id, full_state)
        await session.commit()
        rows = await assets.list_for_version(session, version.id)

    assert len(rows) == 1
    assert rows[0].uri == "s3://bucket/hero.png"
    assert rows[0].checksum == "a" * 64
    assert rows[0].media_type == "image/png"


async def test_second_snapshot_links_to_the_first_and_leaves_it_unchanged(
    session_factory: async_sessionmaker[AsyncSession],
    full_state: WorkflowState,
) -> None:
    run_id, _ = await _run(session_factory)

    async with session_factory() as session:
        first = await snapshot_package(session, run_id, full_state)
        await session.commit()
        original = _row(first)

        revised = full_state.model_copy(update={"copy": REVISED_COPY})
        second = await snapshot_package(session, run_id, revised)
        await session.commit()

        assert second.version == 2
        assert second.parent_version_id == first.id
        assert second.package["copy"] != first.package["copy"]
        stored_first = await session.get(CampaignVersion, first.id)

    assert stored_first is not None
    assert _row(stored_first) == original


async def test_updating_a_version_raises(
    session_factory: async_sessionmaker[AsyncSession],
    full_state: WorkflowState,
) -> None:
    run_id, campaign_id = await _run(session_factory)

    async with session_factory() as session:
        version = await snapshot_package(session, run_id, full_state)
        await session.commit()

        version.package = {"brief": {"product": "rewritten"}}
        with pytest.raises(ImmutableVersionError):
            await session.flush()
        await session.rollback()

        stored = await versions.get(session, campaign_id, 1)

    assert stored is not None
    assert stored.package["brief"]["product"] == "Aurelia Repair Shampoo"
