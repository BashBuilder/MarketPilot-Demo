"""Event envelope and retention rules shared by both bus implementations."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

DEFAULT_EVENT_STREAM_MAXLEN = 2000
DEFAULT_EVENT_STREAM_TTL_SECONDS = 86400
_TERMINAL_EVENTS = frozenset({"awaiting_approval", "completed"})


@dataclass(frozen=True, slots=True)
class EventRecord:
    """One persisted event: its opaque id, type and section-2 body."""

    id: str
    event: str
    data: dict[str, Any]


def event_body(run_id: UUID, agent: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """Build the envelope required by every SSE event in section 2."""
    body: dict[str, Any] = dict(data)
    body["run_id"] = str(run_id)
    body["timestamp"] = datetime.now(UTC).isoformat()
    body["agent"] = agent
    return body


def is_terminal(event_type: str, data: Mapping[str, Any]) -> bool:
    """Return whether the stream should close and expire after this event."""
    return event_type in _TERMINAL_EVENTS or (
        event_type == "error" and data.get("recoverable") is False
    )
