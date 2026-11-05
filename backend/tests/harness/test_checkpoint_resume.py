"""Tests for crash resume and the human approval interrupt."""

from uuid import UUID

import pytest
from context_support import state
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.models import ApprovalDecision, RunStatus
from app.database.repositories import approvals, campaigns, runs, versions
from app.harness.checkpoints import (
    DONE_NODE,
    request_approval,
    resume_point,
    save_checkpoint,
    submit_decision,
)


async def _run_with_version(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Resume test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await versions.create(session, campaign_id=campaign.id, package={"brief": {}})
        await session.commit()
        return run.id


async def _checkpoint(session_factory: async_sessionmaker[AsyncSession], run_id: UUID) -> None:
    async with session_factory() as session:
        await save_checkpoint(session, run_id, "reviewer", state())
        await session.commit()


async def test_crash_after_node_three_resumes_at_node_four(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_with_version(session_factory)

    async with session_factory() as session:
        for node_name in ("brief", "research", "copywriter"):
            await save_checkpoint(session, run_id, node_name, state())
        await session.commit()

    # A fresh session models the process restarting after the crash.
    async with session_factory() as session:
        assert await resume_point(session, run_id) == "creative_director"


async def test_revise_routes_to_the_target_node(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_with_version(session_factory)
    await _checkpoint(session_factory, run_id)

    async with session_factory() as session:
        await request_approval(session, run_id)
        await session.commit()

    async with session_factory() as session:
        paused = await runs.get(session, run_id)
        assert paused is not None
        assert paused.status is RunStatus.AWAITING_APPROVAL
        assert paused.current_node == "human"
        assert await resume_point(session, run_id) == "human"

        next_node = await submit_decision(
            session,
            run_id,
            ApprovalDecision.REVISE,
            comment="Tighten the medical claims",
            target_node="copywriter",
        )
        await session.commit()

    assert next_node == "copywriter"

    async with session_factory() as session:
        run = await runs.get(session, run_id)
        approval = await approvals.get_latest_for_run(session, run_id)

    assert run is not None
    assert run.status is RunStatus.RUNNING
    assert run.current_node == "copywriter"
    assert approval is not None
    assert approval.decision is ApprovalDecision.REVISE
    assert approval.target_node == "copywriter"
    assert approval.comment == "Tighten the medical claims"


async def test_approve_returns_the_done_marker(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_with_version(session_factory)
    await _checkpoint(session_factory, run_id)

    async with session_factory() as session:
        await request_approval(session, run_id)
        next_node = await submit_decision(session, run_id, ApprovalDecision.APPROVE)
        await session.commit()

    assert next_node == DONE_NODE == "end"

    async with session_factory() as session:
        run = await runs.get(session, run_id)
        approval = await approvals.get_latest_for_run(session, run_id)

    assert run is not None
    assert run.status is RunStatus.COMPLETED
    assert run.current_node is None
    assert approval is not None
    assert approval.decision is ApprovalDecision.APPROVE


async def test_revise_requires_a_comment(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _run_with_version(session_factory)
    await _checkpoint(session_factory, run_id)

    async with session_factory() as session:
        await request_approval(session, run_id)
        with pytest.raises(ValueError, match="comment"):
            await submit_decision(session, run_id, ApprovalDecision.REVISE, comment="   ")
