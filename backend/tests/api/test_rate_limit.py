"""Per-IP fixed-window rate limiting for write and read endpoints."""

from collections.abc import Callable

import pytest
from httpx import AsyncClient
from limits_support import FakeRateLimitRedis
from sqlalchemy import func, select

from app.api.limits import RedisRateLimiter
from app.core.config import get_settings
from app.database.models import Campaign


@pytest.fixture()
def configure(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Apply limit-related env values and refresh the settings cache."""

    def _apply(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setenv(key, str(value))
        get_settings.cache_clear()

    return _apply


async def test_twenty_first_write_in_a_minute_is_rejected_with_retry_after(
    client: AsyncClient,
    session_factory,
    configure: Callable[..., None],
) -> None:
    configure(RATE_LIMIT_PER_MINUTE=20, MAX_CONCURRENT_RUNS=100)

    for index in range(20):
        response = await client.post("/api/v1/campaigns", json={"idea": f"Idea {index}"})
        assert response.status_code == 201

    blocked = await client.post("/api/v1/campaigns", json={"idea": "One too many"})

    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "20"
    error = blocked.json()["error"]
    assert error["code"] == "rate_limited"
    assert error["details"]["limit"] == 20
    async with session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(Campaign))
    assert total == 20


async def test_limits_are_tracked_per_forwarded_ip(
    client: AsyncClient,
    configure: Callable[..., None],
) -> None:
    configure(RATE_LIMIT_PER_MINUTE=2, MAX_CONCURRENT_RUNS=100, TRUST_PROXY=True)

    first = {"X-Forwarded-For": "203.0.113.10"}
    second = {"X-Forwarded-For": "203.0.113.11"}
    assert (
        await client.post("/api/v1/campaigns", json={"idea": "A"}, headers=first)
    ).status_code == 201
    assert (
        await client.post("/api/v1/campaigns", json={"idea": "B"}, headers=first)
    ).status_code == 201
    assert (
        await client.post("/api/v1/campaigns", json={"idea": "C"}, headers=first)
    ).status_code == 429
    assert (
        await client.post("/api/v1/campaigns", json={"idea": "D"}, headers=second)
    ).status_code == 201


async def test_forwarded_header_is_ignored_when_proxy_is_untrusted(
    client: AsyncClient,
    configure: Callable[..., None],
) -> None:
    configure(RATE_LIMIT_PER_MINUTE=2, MAX_CONCURRENT_RUNS=100, TRUST_PROXY=False)

    assert (
        await client.post(
            "/api/v1/campaigns", json={"idea": "A"}, headers={"X-Forwarded-For": "203.0.113.20"}
        )
    ).status_code == 201
    assert (
        await client.post(
            "/api/v1/campaigns", json={"idea": "B"}, headers={"X-Forwarded-For": "203.0.113.21"}
        )
    ).status_code == 201
    blocked = await client.post(
        "/api/v1/campaigns", json={"idea": "C"}, headers={"X-Forwarded-For": "203.0.113.22"}
    )
    assert blocked.status_code == 429


async def test_reads_get_a_wider_budget_than_writes(
    client: AsyncClient,
    configure: Callable[..., None],
) -> None:
    configure(RATE_LIMIT_PER_MINUTE=1)

    for _ in range(5):
        assert (await client.get("/api/v1/campaigns")).status_code == 200
    blocked = await client.get("/api/v1/campaigns")

    assert blocked.status_code == 429
    assert blocked.json()["error"]["details"]["scope"] == "read"


async def test_redis_limiter_counts_and_sets_one_ttl_per_window() -> None:
    client = FakeRateLimitRedis()
    limiter = RedisRateLimiter(client, clock=lambda: 1000.0)

    first = await limiter.hit(scope="write", client_ip="198.51.100.7", limit=2)
    second = await limiter.hit(scope="write", client_ip="198.51.100.7", limit=2)
    third = await limiter.hit(scope="write", client_ip="198.51.100.7", limit=2)

    assert (first.allowed, first.retry_after) == (True, 20)
    assert (second.allowed, second.retry_after) == (True, 20)
    assert (third.allowed, third.retry_after) == (False, 20)
    key = "ratelimit:write:198.51.100.7:16"
    assert client.counters[key] == 3
    assert client.expirations == [(key, 60)]
