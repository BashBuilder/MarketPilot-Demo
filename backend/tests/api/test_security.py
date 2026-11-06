"""Boundary validation and error responses must not leak internals."""

from collections.abc import Callable

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from workflow_support import seed_at_gate

from app.core.config import get_settings
from app.main import app


@pytest.fixture()
def configure(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    def _apply(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setenv(key, str(value))
        get_settings.cache_clear()

    return _apply


async def test_idea_length_comes_from_settings(
    client: AsyncClient,
    configure: Callable[..., None],
) -> None:
    configure(MAX_IDEA_LENGTH=5, RATE_LIMIT_PER_MINUTE=100)

    response = await client.post("/api/v1/campaigns", json={"idea": "123456"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"] == {"max_length": 5, "length": 6}


@pytest.mark.parametrize("endpoint", ["approve", "revise"])
async def test_comment_length_comes_from_settings(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    configure: Callable[..., None],
    endpoint: str,
) -> None:
    configure(MAX_COMMENT_LENGTH=10, MAX_CONCURRENT_RUNS=100, RATE_LIMIT_PER_MINUTE=100)
    run_id, _ = await seed_at_gate(session_factory)

    response = await client.post(
        f"/api/v1/runs/{run_id}/{endpoint}",
        json={"comment": "x" * 11},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"] == {"max_length": 10, "length": 11}


async def test_unexpected_error_returns_a_generic_body(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def explode(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("SECRET=super-secret\nTraceback: internals")

    monkeypatch.setattr("app.api.campaigns.campaigns.list_all", explode)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as raw:
        response = await raw.get("/api/v1/campaigns")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }
    body = response.text.lower()
    assert "secret" not in body
    assert "traceback" not in body
    assert "internals" not in body


async def test_cors_never_returns_a_wildcard_origin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"Origin": "*"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
