"""API tests for campaign creation, summaries, errors and CORS."""

from uuid import UUID, uuid4

import pytest
from api_support import FRONTEND_ORIGIN, MAX_IDEA_LENGTH
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import RecordingRunLauncher
from app.core.config import get_settings
from app.database.repositories import versions


async def test_create_list_and_get_return_the_summary_shape(
    client: AsyncClient,
    launcher: RecordingRunLauncher,
) -> None:
    created = await client.post("/api/v1/campaigns", json={"idea": "  Hair care launch  "})

    assert created.status_code == 201
    body = created.json()
    assert set(body) == {"campaign_id", "run_id"}
    assert launcher.started == [UUID(body["run_id"])]

    listing = await client.get("/api/v1/campaigns")
    assert listing.status_code == 200
    summary = listing.json()[0]
    assert summary["id"] == body["campaign_id"]
    assert summary["idea"] == "Hair care launch"
    assert summary["status"] == "draft"
    assert summary["latest_version"] is None
    assert summary["latest_score"] is None
    assert summary["active_run_id"] == body["run_id"]
    assert summary["created_at"]
    assert summary["updated_at"]

    detail = await client.get(f"/api/v1/campaigns/{body['campaign_id']}")
    assert detail.status_code == 200
    assert detail.json() == summary


async def test_summary_reports_the_latest_version_and_score(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    created = await client.post("/api/v1/campaigns", json={"idea": "Hair care launch"})
    campaign_id = UUID(created.json()["campaign_id"])

    async with session_factory() as session:
        await versions.create(
            session,
            campaign_id=campaign_id,
            package={"brief": {}},
            score=88.0,
        )
        await session.commit()

    detail = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert detail.json()["latest_version"] == 1
    assert detail.json()["latest_score"] == 88.0


async def test_unknown_campaign_returns_the_error_shape(client: AsyncClient) -> None:
    missing = uuid4()
    response = await client.get(f"/api/v1/campaigns/{missing}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": f"campaign not found: {missing}",
            "details": {"id": str(missing)},
        }
    }


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"idea": "   "}, "idea must not be blank"),
        (
            {"idea": "x" * (MAX_IDEA_LENGTH + 1)},
            f"idea must be at most {MAX_IDEA_LENGTH} characters",
        ),
    ],
)
async def test_bad_idea_returns_a_422_error_shape(
    client: AsyncClient,
    payload: dict[str, str],
    message: str,
) -> None:
    response = await client.post("/api/v1/campaigns", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["message"] == message


async def test_missing_idea_uses_the_request_validation_shape(client: AsyncClient) -> None:
    response = await client.post("/api/v1/campaigns", json={})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Request validation failed"
    assert error["details"]["errors"][0]["field"] == "body.idea"


async def test_cors_allows_only_the_frontend_origin(client: AsyncClient) -> None:
    allowed = await client.get("/api/v1/health", headers={"Origin": FRONTEND_ORIGIN})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == FRONTEND_ORIGIN

    denied = await client.get("/api/v1/health", headers={"Origin": "http://other.test"})
    assert denied.status_code == 200
    assert "access-control-allow-origin" not in denied.headers


async def test_cors_allows_every_listed_origin(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origins = (
        "http://localhost:3000",
        "https://marketpilot-demo-frontend.vercel.app",
    )
    monkeypatch.setenv("FRONTEND_ORIGIN", ",".join(origins))
    get_settings.cache_clear()

    for origin in origins:
        allowed = await client.get("/api/v1/health", headers={"Origin": origin})
        assert allowed.headers["access-control-allow-origin"] == origin


async def test_cors_tolerates_a_trailing_slash_in_config(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin = "https://marketpilot-demo-frontend.vercel.app"
    monkeypatch.setenv("FRONTEND_ORIGIN", f"http://localhost:3000,{origin}/")
    get_settings.cache_clear()

    allowed = await client.get("/api/v1/health", headers={"Origin": origin})

    assert allowed.headers["access-control-allow-origin"] == origin
