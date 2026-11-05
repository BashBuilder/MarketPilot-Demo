"""JSON structured logging with per-run context propagated through context vars."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any, Final

run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
campaign_id_var: ContextVar[str | None] = ContextVar("campaign_id", default=None)
agent_var: ContextVar[str | None] = ContextVar("agent", default=None)
step_var: ContextVar[str | None] = ContextVar("step", default=None)

_CONTEXT_VARS: Final[dict[str, ContextVar[str | None]]] = {
    "run_id": run_id_var,
    "campaign_id": campaign_id_var,
    "agent": agent_var,
    "step": step_var,
}


@contextmanager
def bind_run_context(
    *,
    run_id: str | None = None,
    campaign_id: str | None = None,
    agent: str | None = None,
    step: str | None = None,
) -> Iterator[None]:
    """Attach run context to every log record emitted inside the block.

    Values are restored on exit so concurrent requests and runs never leak
    identifiers into one another.
    """
    tokens: list[tuple[ContextVar[str | None], Token[str | None]]] = []
    for var, value in (
        (run_id_var, run_id),
        (campaign_id_var, campaign_id),
        (agent_var, agent),
        (step_var, step),
    ):
        if value is not None:
            tokens.append((var, var.set(value)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


class JsonFormatter(logging.Formatter):
    """Render one log record per line as JSON with run context attached."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for name, var in _CONTEXT_VARS.items():
            value = getattr(record, name, None)
            if value is None:
                value = var.get()
            if value is not None:
                payload[name] = value
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install JSON output on the root logger, idempotently."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    if any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
