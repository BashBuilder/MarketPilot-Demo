"""Redis fixed-window rate limiting for HTTP endpoints.

The window key is scoped by operation, client IP and minute so a busy GET
stream never eats the write budget. Proxies are only trusted when explicitly
configured; otherwise a spoofed ``X-Forwarded-For`` changes nothing.
"""

import ipaddress
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Protocol, cast

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.errors import RateLimited

__all__ = [
    "READ_SCOPE",
    "WRITE_SCOPE",
    "RedisRateLimiter",
    "RateLimiter",
    "client_ip",
    "enforce_read_limit",
    "enforce_write_limit",
    "get_rate_limiter",
]

WINDOW_SECONDS = 60
# Reads are polled more often than writes, so they get a wider budget without
# needing another environment variable.
READ_LIMIT_MULTIPLIER = 5
WRITE_SCOPE = "write"
READ_SCOPE = "read"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Whether one request fits the window and when the window resets."""

    allowed: bool
    retry_after: int


class RateLimitClient(Protocol):
    """The two Redis commands a fixed-window counter needs."""

    async def incr(self, key: str) -> int: ...

    async def expire(self, key: str, seconds: int) -> bool: ...


class RateLimiter(Protocol):
    """Request-budget check used by the FastAPI dependencies."""

    async def hit(self, *, scope: str, client_ip: str, limit: int) -> RateLimitDecision: ...


class RedisRateLimiter:
    """Count requests per IP and minute with Redis INCR/EXPIRE."""

    def __init__(
        self,
        client: RateLimitClient,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._clock = clock

    @classmethod
    def from_url(cls, url: str) -> "RedisRateLimiter":
        client = cast(RateLimitClient, Redis.from_url(url, decode_responses=True))
        return cls(client)

    async def hit(self, *, scope: str, client_ip: str, limit: int) -> RateLimitDecision:
        now = self._clock()
        window = int(now) // WINDOW_SECONDS
        retry_after = WINDOW_SECONDS - int(now) % WINDOW_SECONDS
        key = f"ratelimit:{scope}:{client_ip}:{window}"
        count = await self._client.incr(key)
        if count == 1:
            await self._client.expire(key, WINDOW_SECONDS)
        return RateLimitDecision(
            allowed=count <= limit,
            retry_after=max(1, retry_after),
        )


def get_rate_limiter(request: Request) -> RateLimiter:
    """Return the process-wide limiter installed by the application."""
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        raise RuntimeError("rate limiter is not configured")
    return cast(RateLimiter, limiter)


async def enforce_write_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    """Apply the configured per-minute budget to mutating requests."""
    await _enforce(
        request,
        limiter,
        scope=WRITE_SCOPE,
        limit=settings.rate_limit_per_minute,
        trust_proxy=settings.trust_proxy,
    )


async def enforce_read_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    """Apply the wider read budget so polling clients are not starved."""
    await _enforce(
        request,
        limiter,
        scope=READ_SCOPE,
        limit=settings.rate_limit_per_minute * READ_LIMIT_MULTIPLIER,
        trust_proxy=settings.trust_proxy,
    )


async def _enforce(
    request: Request,
    limiter: RateLimiter,
    *,
    scope: str,
    limit: int,
    trust_proxy: bool,
) -> None:
    address = client_ip(request, trust_proxy=trust_proxy)
    decision = await limiter.hit(scope=scope, client_ip=address, limit=limit)
    if not decision.allowed:
        raise RateLimited(
            f"rate limit exceeded; retry after {decision.retry_after} seconds",
            retry_after=decision.retry_after,
            details={"limit": limit, "scope": scope, "retry_after": decision.retry_after},
        )


def client_ip(request: Request, *, trust_proxy: bool) -> str:
    """Resolve the caller address, honouring forwarded headers only when trusted."""
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if _is_ip(candidate):
                return candidate
    if request.client is not None:
        return request.client.host
    return "unknown"


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True
