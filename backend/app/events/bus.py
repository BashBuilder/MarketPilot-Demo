"""Run event streams backed by Redis Streams or memory.

The stored record id is the replay cursor: clients send the last id they saw
as ``Last-Event-ID`` and the server resumes strictly after it. Redis keys are
``run:{run_id}:events``, one stream per run, so replay never scans other runs.
"""

import json
from collections import deque
from collections.abc import Mapping
from itertools import count
from typing import Any, Protocol
from uuid import UUID

from redis.asyncio import Redis

from app.events.envelope import (
    DEFAULT_EVENT_STREAM_MAXLEN,
    DEFAULT_EVENT_STREAM_TTL_SECONDS,
    EventRecord,
    event_body,
    is_terminal,
)

__all__ = ["EventBus", "EventRecord", "InMemoryEventBus", "RedisEventBus", "event_body"]


class EventBus(Protocol):
    """Durable, replayable transport shared by the harness and the API."""

    async def publish(
        self,
        run_id: UUID,
        event_type: str,
        agent: str,
        data: Mapping[str, Any],
    ) -> str: ...

    async def read(self, run_id: UUID, after_id: str | None) -> list[EventRecord]: ...


class InMemoryEventBus:
    """Deterministic bus for tests; ids sort lexicographically like stream ids."""

    def __init__(self, maxlen: int = DEFAULT_EVENT_STREAM_MAXLEN) -> None:
        if maxlen < 1:
            raise ValueError("maxlen must be positive")
        self._maxlen = maxlen
        self._streams: dict[UUID, deque[EventRecord]] = {}
        self._sequence = count(1)

    async def publish(
        self,
        run_id: UUID,
        event_type: str,
        agent: str,
        data: Mapping[str, Any],
    ) -> str:
        event_id = f"{next(self._sequence):020d}-0"
        record = EventRecord(id=event_id, event=event_type, data=event_body(run_id, agent, data))
        self._streams.setdefault(run_id, deque(maxlen=self._maxlen)).append(record)
        return event_id

    async def read(self, run_id: UUID, after_id: str | None) -> list[EventRecord]:
        stream = self._streams.get(run_id)
        if stream is None:
            return []
        if after_id is None:
            return list(stream)
        return [record for record in stream if record.id > after_id]


class RedisEventBus:
    """Redis Streams implementation used by the running service."""

    def __init__(
        self,
        client: Redis,
        *,
        maxlen: int = DEFAULT_EVENT_STREAM_MAXLEN,
        ttl_seconds: int = DEFAULT_EVENT_STREAM_TTL_SECONDS,
    ) -> None:
        if maxlen < 1 or ttl_seconds < 1:
            raise ValueError("maxlen and ttl_seconds must be positive")
        self._client = client
        self._maxlen = maxlen
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        maxlen: int = DEFAULT_EVENT_STREAM_MAXLEN,
        ttl_seconds: int = DEFAULT_EVENT_STREAM_TTL_SECONDS,
    ) -> "RedisEventBus":
        return cls(
            Redis.from_url(url, decode_responses=True),
            maxlen=maxlen,
            ttl_seconds=ttl_seconds,
        )

    @staticmethod
    def key(run_id: UUID) -> str:
        return f"run:{run_id}:events"

    async def publish(
        self,
        run_id: UUID,
        event_type: str,
        agent: str,
        data: Mapping[str, Any],
    ) -> str:
        payload = event_body(run_id, agent, data)
        body = json.dumps(payload, separators=(",", ":"), default=str)
        stored = await self._client.xadd(
            self.key(run_id),
            {"event": event_type, "data": body},
            maxlen=self._maxlen,
            approximate=True,
        )
        if is_terminal(event_type, payload):
            await self._client.expire(self.key(run_id), self._ttl_seconds)
        return _as_text(stored)

    async def read(self, run_id: UUID, after_id: str | None) -> list[EventRecord]:
        start = f"({after_id}" if after_id else "-"
        rows = await self._client.xrange(self.key(run_id), min=start, max="+")
        records: list[EventRecord] = []
        for event_id, fields in rows or []:
            if fields is not None:
                records.append(self._record(event_id, fields))
        return records

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _record(event_id: Any, fields: Mapping[Any, Any]) -> EventRecord:
        raw = fields.get("data", "{}")
        return EventRecord(
            id=_as_text(event_id),
            event=_as_text(fields["event"]),
            data=json.loads(raw),
        )


def _as_text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)
