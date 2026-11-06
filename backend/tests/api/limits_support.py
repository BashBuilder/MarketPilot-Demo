"""Fake Redis client and limiter factory for API rate-limit tests."""

from app.api.limits import RedisRateLimiter

# A frozen clock keeps Retry-After deterministic: 1000 % 60 leaves 20 seconds.
FIXED_NOW = 1000.0


class FakeRateLimitRedis:
    """In-memory INCR/EXPIRE client with inspectable command history."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expirations: list[tuple[str, int]] = []

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.expirations.append((key, seconds))
        return True


def make_rate_limiter(now: float = FIXED_NOW) -> RedisRateLimiter:
    """Build a limiter backed by the fake client and a frozen clock."""
    return RedisRateLimiter(FakeRateLimitRedis(), clock=lambda: now)
