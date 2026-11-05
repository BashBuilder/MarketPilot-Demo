"""Retry-with-feedback loop for agent output that fails verification."""

from typing import Any

import pytest
from support import settings

from app.agents.outputs import AdCopySet
from app.core.errors import RetryExhausted
from app.harness.verification import (
    CopySemanticValidator,
    VerificationEvent,
    run_with_verification,
)

VALID = {
    "variants": [
        {
            "channel": "Instagram",
            "headline": "Repair starts here",
            "description": "A weekly ritual for colour-treated hair.",
            "cta": "Shop now",
        }
    ]
}

INVALID = {
    "variants": [
        {
            "channel": "Instagram",
            "headline": "x" * 41,
            "description": "A weekly ritual for colour-treated hair.",
            "cta": "Shop now",
        }
    ]
}

HEADLINE_ISSUE = "variant 1 (Instagram): headline is 41 characters; limit is 40"


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


async def test_invalid_then_valid_returns_the_parsed_model() -> None:
    prompts: list[str] = []
    payloads = [INVALID, VALID]

    async def step(feedback: str) -> Any:
        prompts.append(feedback)
        return payloads[len(prompts) - 1]

    result = await run_with_verification(
        step,
        model=AdCopySet,
        semantic=CopySemanticValidator(),
        settings=settings(retry_max_attempts=2),
        sleep=SleepRecorder(),
        jitter=lambda: 0.0,
    )

    assert isinstance(result, AdCopySet)
    assert result.variants[0].headline == "Repair starts here"
    assert len(prompts) == 2
    assert prompts[0] == ""


async def test_feedback_from_the_previous_attempt_reaches_the_next_prompt() -> None:
    prompts: list[str] = []
    payloads = [INVALID, VALID]

    async def step(feedback: str) -> Any:
        prompts.append(feedback)
        return payloads[len(prompts) - 1]

    await run_with_verification(
        step,
        model=AdCopySet,
        semantic=CopySemanticValidator(),
        settings=settings(retry_max_attempts=2),
        sleep=SleepRecorder(),
        jitter=lambda: 0.0,
    )

    assert HEADLINE_ISSUE in prompts[1]
    assert "Fix every issue and return the full output again." in prompts[1]


async def test_exhausted_attempts_raise_retry_exhausted() -> None:
    events: list[VerificationEvent] = []
    sleeps = SleepRecorder()
    calls = 0

    async def step(feedback: str) -> Any:
        nonlocal calls
        calls += 1
        return INVALID

    async def on_event(event: VerificationEvent) -> None:
        events.append(event)

    with pytest.raises(RetryExhausted) as excinfo:
        await run_with_verification(
            step,
            model=AdCopySet,
            semantic=CopySemanticValidator(),
            on_event=on_event,
            settings=settings(retry_max_attempts=2),
            sleep=sleeps,
            jitter=lambda: 0.0,
        )

    assert calls == 2
    assert sleeps.delays == [0.5]
    assert [event.event for event in events] == [
        "validation_failed",
        "retrying",
        "validation_failed",
    ]
    assert events[0].attempt == 1
    assert events[1].attempt == 1
    assert events[1].max_attempts == 2
    assert events[1].delay == 0.5
    assert HEADLINE_ISSUE in events[1].issues
    assert excinfo.value.details["attempts"] == 2
    assert HEADLINE_ISSUE in excinfo.value.details["issues"]
    assert HEADLINE_ISSUE in str(excinfo.value)
