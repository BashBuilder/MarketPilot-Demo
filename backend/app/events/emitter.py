"""Adapters between the event bus and the harness event-emitter shape.

The harness emits ``(event_type, data)`` where data already carries the run and
agent envelope. The bus owns persistence and timestamps, so the adapter strips
the envelope and lets the bus rebuild it.
"""

from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from app.events.bus import EventBus

type EventPublisher = Callable[[str, Mapping[str, Any]], Awaitable[None]]

_ENVELOPE_KEYS = frozenset({"run_id", "timestamp", "agent"})
_emitter: ContextVar[EventPublisher | None] = ContextVar("run_event_emitter", default=None)


def make_emitter(bus: EventBus) -> EventPublisher:
    """Turn a bus into the callback the node wrapper and middleware expect."""

    async def emit(event_type: str, data: Mapping[str, Any]) -> None:
        raw_run_id = data.get("run_id")
        if raw_run_id is None:
            raise ValueError(f"{event_type} event is missing run_id")
        payload = {key: value for key, value in data.items() if key not in _ENVELOPE_KEYS}
        await bus.publish(
            UUID(str(raw_run_id)),
            event_type,
            str(data.get("agent", "")),
            payload,
        )

    return emit


@contextmanager
def bind_event_emitter(emitter: EventPublisher) -> Iterator[None]:
    """Expose an emitter to code that cannot receive it as an argument."""
    token = _emitter.set(emitter)
    try:
        yield
    finally:
        _emitter.reset(token)


def current_event_emitter() -> EventPublisher | None:
    """Return the emitter bound to the current task, if any."""
    return _emitter.get()
