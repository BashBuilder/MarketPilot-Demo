"""Typed exceptions shared across the backend."""

from typing import Any, ClassVar


class MarketPilotError(Exception):
    """Base error carrying a stable API code and structured details."""

    code: ClassVar[str] = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ToolError(MarketPilotError):
    """A tool call failed and the caller must decide whether to retry."""

    code = "tool_error"


class ValidationFailure(MarketPilotError):
    """An agent output failed schema or semantic validation."""

    code = "validation_failed"


class GuardrailViolation(MarketPilotError):
    """An agent attempted an action outside its allowlist or policy."""

    code = "guardrail_violation"


class RetryExhausted(MarketPilotError):
    """A node exhausted its retry budget and must escalate."""

    code = "retry_exhausted"
