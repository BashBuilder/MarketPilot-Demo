"""Database-backed cap on concurrently running workflow runs."""

from collections.abc import Callable
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_support import seed_at_gate

from app.api.dependencies import RecordingRunLauncher
from app.core.config import get_settings
from app.database.models import Approval, Campaign, CampaignVersion, RunStatus, WorkflowRun
from app.database.repositories import campaigns, runs


@pytest.fixture()
def configure(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    def _apply(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setenv(key, str(value))
        get_settings.cache_clear()

    return _apply


async def _count(session_factory, model: type) -> int:
    async with session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(model))
    return int(total or 0)


async def _seed_running(
    session_factory: async_sessionmaker[AsyncSession],
    count: int,
) -> list[UUID]:
    ids: list[UUID] = []
    async with session_factory() as session:
        for index in range(count):
            campaign = await campaigns.create(session, idea=f"Running campaign {index}")
            run = await runs.create(session, campaign_id=campaign.id)
            await runs.set_status(session, run.id, RunStatus.RUNNING, current_node="brief")
            ids.append(run.id)
        await session.commit()
    return ids


async def test_fourth_campaign_is_blocked_and_creates_no_rows(
    client: AsyncClient,
    launcher: RecordingRunLauncher,
    session_factory: async_sessionmaker[AsyncSession],
    configure: Callable[..., None],
) -> None:
    configure(MAX_CONCURRENT_RUNS=3, RATE_LIMIT_PER_MINUTE=100)
    await _seed_running(session_factory, 3)
    campaigns_before = await _count(session_factory, Campaign)
    runs_before = await _count(session_factory, WorkflowRun)

    response = await client.post("/api/v1/campaigns", json={"idea": "One too many"})

    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "too_many_runs"
    assert error["details"] == {"limit": 3, "running": 3}
    assert await _count(session_factory, Campaign) == campaigns_before
    assert await _count(session_factory, WorkflowRun) == runs_before
    assert launcher.started == []


async def test_revise_is_blocked_at_the_cap_without_writing_anything(
    client: AsyncClient,
    launcher: RecordingRunLauncher,
    session_factory: async_sessionmaker[AsyncSession],
    configure: Callable[..., None],
) -> None:
    configure(MAX_CONCURRENT_RUNS=3, RATE_LIMIT_PER_MINUTE=100)
    gate_run, campaign_id = await seed_at_gate(session_factory)
    await _seed_running(session_factory, 3)
    versions_before = await _count(session_factory, CampaignVersion)
    approvals_before = await _count(session_factory, Approval)

    response = await client.post(
        f"/api/v1/runs/{gate_run}/revise",
        json={"comment": "Try again", "target_node": "reviewer"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_runs"
    async with session_factory() as session:
        stored = await runs.get(session, gate_run)
        latest_version = await session.scalar(
            select(func.count())
            .select_from(CampaignVersion)
            .where(CampaignVersion.campaign_id == campaign_id)
        )
    assert stored is not None and stored.status is RunStatus.AWAITING_APPROVAL
    assert latest_version == versions_before == 1
    assert await _count(session_factory, Approval) == approvals_before == 0
    assert launcher.started == []
