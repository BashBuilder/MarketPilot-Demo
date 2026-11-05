"""Retry policy: transient-only, bounded attempts, instant in tests."""

from typing import Any

import pytest

from app.core.errors import RetryExhausted, ToolError
from app.harness.retries import retry_async


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


async def test_retryable_failure_then_success() -> None:
    sleep = SleepRecorder()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ToolError("temporary outage", retryable=True)
        return "ok"

    result = await retry_async(operation, max_attempts=3, sleep=sleep, jitter=lambda: 0.0)

    assert result == "ok"
    assert calls == 2
    assert len(sleep.delays) == 1


async def test_non_retryable_error_is_not_retried() -> None:
    sleep = SleepRecorder()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        raise ToolError("permanent failure")

    with pytest.raises(ToolError, match="permanent failure"):
        await retry_async(operation, max_attempts=3, sleep=sleep)

    assert calls == 1
    assert sleep.delays == []


async def test_non_tool_error_is_not_retried() -> None:
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        raise ValueError("bug in the operation")

    with pytest.raises(ValueError, match="bug in the operation"):
        await retry_async(operation, max_attempts=3, sleep=SleepRecorder())

    assert calls == 1


async def test_exhausted_attempts_raise_retry_exhausted() -> None:
    sleep = SleepRecorder()
    errors: list[ToolError] = []

    async def operation() -> str:
        error = ToolError(f"failure {len(errors) + 1}", retryable=True)
        errors.append(error)
        raise error

    with pytest.raises(RetryExhausted) as excinfo:
        await retry_async(operation, max_attempts=3, sleep=sleep, jitter=lambda: 0.0)

    assert len(errors) == 3
    assert excinfo.value.__cause__ is errors[-1]
    assert excinfo.value.details["attempts"] == 3
    assert excinfo.value.details["last_error"] == "failure 3"
    assert len(sleep.delays) == 2


async def test_fallback_runs_after_last_failed_attempt() -> None:
    sleep = SleepRecorder()
    received: list[ToolError] = []
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        raise ToolError("still down", retryable=True)

    async def fallback(error: ToolError) -> str:
        received.append(error)
        return "cached result"

    result = await retry_async(
        operation, max_attempts=2, fallback=fallback, sleep=sleep, jitter=lambda: 0.0
    )

    assert result == "cached result"
    assert calls == 2
    assert len(received) == 1
    assert received[0].message == "still down"
    assert len(sleep.delays) == 1


async def test_backoff_grows_exponentially_and_respects_the_cap() -> None:
    sleep = SleepRecorder()

    async def operation() -> Any:
        raise ToolError("down", retryable=True)

    with pytest.raises(RetryExhausted):
        await retry_async(
            operation,
            max_attempts=4,
            sleep=sleep,
            base_delay=1.0,
            max_delay=3.0,
            jitter=lambda: 0.0,
        )

    assert sleep.delays == [1.0, 2.0, 3.0]


async def test_invalid_max_attempts_is_rejected() -> None:
    async def operation() -> str:
        return "never called"

    with pytest.raises(ValueError, match="at least 1"):
        await retry_async(operation, max_attempts=0)
