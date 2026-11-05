"""Tests for append-only checkpoint persistence and state re-validation."""

from uuid import UUID

import pytest
from context_support import state
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ValidationFailure
from app.database.models import ImmutableRowError
from app.database.repositories import campaigns, checkpoints, runs
from app.harness.checkpoints import load_latest_checkpoint, save_checkpoint


async def _run_id(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Checkpoint test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id


async def test_save_then_load_returns_an_equal_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(session_factory)
    original = state()

    async with session_factory() as session:
        await save_checkpoint(session, run_id, "brief", original)
        await session.commit()

    async with session_factory() as session:
        loaded = await load_latest_checkpoint(session, run_id)

    assert loaded == original


async def test_latest_of_several_checkpoints_is_returned(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(session_factory)
    saved = [state(idea=f"Checkpoint idea {index}") for index in range(3)]

    async with session_factory() as session:
        for node_name, checkpoint_state in zip(
            ("brief", "research", "copywriter"), saved, strict=True
        ):
            await save_checkpoint(session, run_id, node_name, checkpoint_state)
        await session.commit()

    async with session_factory() as session:
        loaded = await load_latest_checkpoint(session, run_id)
        rows = await checkpoints.list_for_run(session, run_id)

    assert loaded == saved[-1]
    assert [row.step for row in rows] == [1, 2, 3]


async def test_corrupt_stored_state_raises_validation_failure(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(session_factory)

    async with session_factory() as session:
        await checkpoints.create(session, run_id=run_id, node="brief", state={"idea": ""})
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(ValidationFailure, match="failed state validation"):
            await load_latest_checkpoint(session, run_id)


async def test_missing_checkpoint_returns_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(session_factory)

    async with session_factory() as session:
        assert await load_latest_checkpoint(session, run_id) is None


async def test_checkpoints_cannot_be_updated(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_id(session_factory)

    async with session_factory() as session:
        checkpoint = await save_checkpoint(session, run_id, "brief", state())
        await session.commit()

        checkpoint.node = "research"
        with pytest.raises(ImmutableRowError):
            await session.flush()
