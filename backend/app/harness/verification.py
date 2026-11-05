"""Schema and semantic verification, plus retries with issue feedback.

Pydantic enforces shape, so the semantic validators only check what a schema
cannot. A failed attempt is retried with the real issue text in the next
prompt: a model can only fix what it can see.
"""

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.core.errors import RetryExhausted
from app.harness.retries import Sleep, backoff_delay, default_sleep
from app.harness.validators import (
    MAX_HEADLINE_LENGTH,
    AssetSemanticValidator,
    CopySemanticValidator,
    Issue,
)

__all__ = [
    "MAX_HEADLINE_LENGTH",
    "AssetSemanticValidator",
    "CopySemanticValidator",
    "Issue",
    "Validator",
    "VerificationEvent",
    "run_with_verification",
    "verify_output",
]

type Step = Callable[[str], Awaitable[Any]]
type EventCallback = Callable[["VerificationEvent"], Awaitable[None]]


class Validator[T](Protocol):
    """A semantic check over already schema-valid output."""

    def validate(self, value: T) -> list[Issue]: ...


@dataclass(frozen=True, slots=True)
class VerificationEvent:
    """Progress the caller can publish; SSE wiring happens later."""

    event: Literal["validation_failed", "retrying"]
    attempt: int
    max_attempts: int
    issues: tuple[Issue, ...] = ()
    delay: float | None = None


def verify_output[T: BaseModel](
    model: type[T],
    payload: Any,
    semantic: Validator[T] | None = None,
) -> tuple[T | None, list[Issue]]:
    """Parse then semantically check; stop before semantics on schema failure."""
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        return None, _schema_issues(exc)

    issues = semantic.validate(parsed) if semantic is not None else []
    return parsed, list(issues)


async def run_with_verification[T: BaseModel](
    step: Step,
    *,
    model: type[T],
    semantic: Validator[T] | None = None,
    on_event: EventCallback | None = None,
    settings: Settings | None = None,
    sleep: Sleep = default_sleep,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    jitter: Callable[[], float] = random.random,
) -> T:
    """Run an agent step until its output verifies, then return the model.

    ``step`` receives the previous attempt's issue text (empty on the first
    attempt). Validation failures are the only retried outcome; exceptions
    raised by the step propagate untouched.
    """
    limits = settings if settings is not None else get_settings()
    attempts = limits.retry_max_attempts
    feedback = ""
    issues: list[Issue] = []

    for attempt in range(1, attempts + 1):
        payload = await step(feedback)
        parsed, issues = verify_output(model, payload, semantic)
        if parsed is not None and not issues:
            return parsed

        await _emit(
            on_event,
            VerificationEvent("validation_failed", attempt, attempts, tuple(issues)),
        )
        if attempt == attempts:
            break

        delay = backoff_delay(attempt, base_delay, max_delay, jitter())
        await _emit(
            on_event,
            VerificationEvent("retrying", attempt, attempts, tuple(issues), delay),
        )
        feedback = _feedback(issues)
        await sleep(delay)

    raise RetryExhausted(
        f"output failed verification after {attempts} attempts: {'; '.join(issues)}",
        details={"attempts": attempts, "issues": issues},
    )


def _feedback(issues: list[Issue]) -> str:
    lines = "\n".join(f"- {issue}" for issue in issues)
    return (
        f"The previous output failed verification:\n{lines}\n"
        "Fix every issue and return the full output again."
    )


async def _emit(callback: EventCallback | None, event: VerificationEvent) -> None:
    if callback is not None:
        await callback(event)


def _schema_issues(exc: ValidationError) -> list[Issue]:
    issues: list[Issue] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "value"
        issues.append(f"{location}: {error['msg']}")
    return issues
