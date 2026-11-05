"""API tests for run approval and revision endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_support import reviewer_services, seed_at_gate

from app.api.dependencies import get_workflow_services
from app.database.models import RunStatus
from app.database.repositories import campaigns, runs, versions
from app.main import app


async def test_approve_completes_the_run(client: AsyncClient, session_factory) -> None:
    run_id, _ = await seed_at_gate(session_factory)

    response = await client.post(
        f"/api/v1/runs/{run_id}/approve",
        json={"comment": "Looks good"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "completed", "version": 1}
    async with session_factory() as session:
        stored = await runs.get(session, run_id)
    assert stored is not None
    assert stored.status is RunStatus.COMPLETED


async def test_revise_starts_a_new_run_and_launches_it(
    client: AsyncClient,
    launcher,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id, campaign_id = await seed_at_gate(session_factory)
    app.dependency_overrides[get_workflow_services] = lambda: reviewer_services()

    response = await client.post(
        f"/api/v1/runs/{run_id}/revise",
        json={"comment": "Raise the score", "target_node": "reviewer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert launcher.started == [UUID(body["run_id"])]
    async with session_factory() as session:
        old_run = await runs.get(session, run_id)
        new_run = await runs.get(session, UUID(body["run_id"]))
        latest = await versions.get_latest(session, campaign_id)
    assert old_run is not None and old_run.status is RunStatus.COMPLETED
    assert new_run is not None and new_run.status is RunStatus.AWAITING_APPROVAL
    assert latest is not None and latest.version == 2


@pytest.mark.parametrize(
    ("endpoint", "body"),
    [("approve", {}), ("revise", {"comment": "Try again"})],
)
async def test_deciding_a_run_not_awaiting_approval_returns_409(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    endpoint: str,
    body: dict[str, str],
) -> None:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Not at the gate")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        run_id = run.id

    response = await client.post(f"/api/v1/runs/{run_id}/{endpoint}", json=body)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "invalid_run_state"
    assert error["details"]["status"] == "pending"


async def test_revise_requires_a_non_empty_comment(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id, _ = await seed_at_gate(session_factory)

    response = await client.post(
        f"/api/v1/runs/{run_id}/revise",
        json={"comment": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "revise requires a non-empty comment"


async def test_revise_requires_the_comment_field(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id, _ = await seed_at_gate(session_factory)

    response = await client.post(
        f"/api/v1/runs/{run_id}/revise",
        json={"target_node": "reviewer"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["message"] == "Request validation failed"
    assert error["details"]["errors"][0]["field"] == "body.comment"


async def test_revise_rejects_an_unknown_target_node(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id, _ = await seed_at_gate(session_factory)

    response = await client.post(
        f"/api/v1/runs/{run_id}/revise",
        json={"comment": "Try again", "target_node": "marketing"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"]["target_node"] == "marketing"
    assert "supervisor" in error["details"]["allowed"]


@pytest.mark.parametrize(
    ("endpoint", "body"),
    [("approve", {}), ("revise", {"comment": "Try again"})],
)
async def test_unknown_run_returns_404(
    client: AsyncClient,
    endpoint: str,
    body: dict[str, str],
) -> None:
    missing = uuid4()

    response = await client.post(f"/api/v1/runs/{missing}/{endpoint}", json=body)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
