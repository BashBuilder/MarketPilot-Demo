"""Server-Sent Events endpoint for live run activity and replay.

The stream is a pure function of the event bus plus the client's cursor. Each
frame carries the stream id, so a dropped connection can resume strictly after
the last event the client processed.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_event_bus, get_session
from app.api.limits import enforce_read_limit
from app.core.errors import NotFoundError
from app.database.repositories import runs
from app.events.bus import EventBus
from app.events.envelope import EventRecord

router = APIRouter(prefix="/runs", tags=["runs"])

HEARTBEAT_SECONDS = 15.0
POLL_SECONDS = 0.1
_TERMINAL_EVENTS = frozenset({"awaiting_approval", "completed"})


@router.get(
    "/{run_id}/stream",
    dependencies=[Depends(enforce_read_limit)],
)
async def stream_run(
    run_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    bus: Annotated[EventBus, Depends(get_event_bus)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Replay events after ``Last-Event-ID`` then follow until a terminal event."""
    if await runs.get(session, run_id) is None:
        raise NotFoundError(f"run not found: {run_id}", details={"id": str(run_id)})
    return StreamingResponse(
        _event_stream(bus, run_id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_stream(
    bus: EventBus,
    run_id: UUID,
    after_id: str | None,
) -> AsyncIterator[str]:
    """Yield replay frames, then new frames, with a comment heartbeat."""
    cursor = after_id or None
    last_activity = time.monotonic()
    while True:
        records = await bus.read(run_id, cursor)
        for record in records:
            cursor = record.id
            last_activity = time.monotonic()
            yield _format_event(record)
            if _is_terminal(record):
                return
        if time.monotonic() - last_activity >= HEARTBEAT_SECONDS:
            yield ": heartbeat\n\n"
            last_activity = time.monotonic()
        if not records:
            await asyncio.sleep(POLL_SECONDS)


def _format_event(record: EventRecord) -> str:
    body = json.dumps(record.data, separators=(",", ":"), default=str)
    return f"id: {record.id}\nevent: {record.event}\ndata: {body}\n\n"


def _is_terminal(record: EventRecord) -> bool:
    if record.event in _TERMINAL_EVENTS:
        return True
    return record.event == "error" and record.data.get("recoverable") is False
