"""Tests for the typed exception hierarchy."""

import pytest

from app.core.errors import (
    GuardrailViolation,
    InvalidRunState,
    MarketPilotError,
    RetryExhausted,
    ToolError,
    ValidationFailure,
)


@pytest.mark.parametrize(
    ("error_class", "code"),
    [
        (ToolError, "tool_error"),
        (ValidationFailure, "validation_failed"),
        (GuardrailViolation, "guardrail_violation"),
        (RetryExhausted, "retry_exhausted"),
        (InvalidRunState, "invalid_run_state"),
    ],
)
def test_error_carries_stable_code_and_details(
    error_class: type[MarketPilotError], code: str
) -> None:
    error = error_class("something failed", details={"attempt": 2})

    assert error.code == code
    assert str(error) == "something failed"
    assert error.details == {"attempt": 2}


def test_details_default_to_empty_dict() -> None:
    assert ToolError("boom").details == {}
