"""Retry policy for harness operations: bounded attempts, backoff, fallback.

Only failures that declare themselves transient are retried; a permanent tool
error or a programming error must surface immediately instead of burning the
run's budget on attempts that cannot succeed.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable

from app.core.config import get_settings
from app.core.errors import RetryExhausted, ToolError

type Sleep = Callable[[float], Awaitable[None]]


async def default_sleep(delay: float) -> None:
    await asyncio.sleep(delay)


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int | None = None,
    fallback: Callable[[ToolError], Awaitable[T]] | None = None,
    sleep: Sleep = default_sleep,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    jitter: Callable[[], float] = random.random,
) -> T:
    """Run an operation with bounded retries and optional fallback.

    ``max_attempts`` defaults to the configured retry budget. Sleep and jitter
    are injectable so tests exercise the policy without waiting.
    """
    attempts = max_attempts if max_attempts is not None else get_settings().retry_max_attempts
    if attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("retry delays must not be negative")

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except ToolError as exc:
            if not exc.retryable:
                raise
            if attempt == attempts:
                if fallback is not None:
                    return await fallback(exc)
                raise RetryExhausted(
                    f"retry budget exhausted after {attempts} attempts: {exc.message}",
                    details={"attempts": attempts, "last_error": exc.message},
                ) from exc
            await sleep(backoff_delay(attempt, base_delay, max_delay, jitter()))

    raise AssertionError("unreachable: the retry loop returns or raises")


def backoff_delay(attempt: int, base_delay: float, max_delay: float, jitter: float) -> float:
    """Exponential delay with jitter, capped so a run cannot stall unbounded."""
    exponential = base_delay * 2.0 ** (attempt - 1)
    return max(0.0, min(max_delay, exponential * (1 + jitter)))
