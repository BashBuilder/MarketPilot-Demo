"""Run event streams backed by Redis Streams or memory.

The stored record id is the replay cursor: clients send the last id they saw
as ``Last-Event-ID`` and the server resumes strictly after it. Redis keys are
``run:{run_id}:events``, one stream per run, so replay never scans other runs.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import count
from typing import Any, Protocol
from uuid import UUID

from redis.asyncio import Redis


@dataclass(frozen=True, slots=True)
class EventRecord:
    """One persisted event: its opaque id, type and section-2 body."""

    id: str
    event: str
    data: dict[str, Any]


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


def event_body(run_id: UUID, agent: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """Build the envelope required by every SSE event in section 2."""
    body: dict[str, Any] = dict(data)
    body["run_id"] = str(run_id)
    body["timestamp"] = datetime.now(UTC).isoformat()
    body["agent"] = agent
    return body


class InMemoryEventBus:
    """Deterministic bus for tests; ids sort lexicographically like stream ids."""

    def __init__(self) -> None:
        self._streams: dict[UUID, list[EventRecord]] = {}
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
        self._streams.setdefault(run_id, []).append(record)
        return event_id

    async def read(self, run_id: UUID, after_id: str | None) -> list[EventRecord]:
        records = self._streams.get(run_id, [])
        if after_id is None:
            return list(records)
        return [record for record in records if record.id > after_id]


class RedisEventBus:
    """Redis Streams implementation used by the running service."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisEventBus":
        return cls(Redis.from_url(url, decode_responses=True))

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
        body = json.dumps(event_body(run_id, agent, data), separators=(",", ":"), default=str)
        stored = await self._client.xadd(
            self.key(run_id),
            {"event": event_type, "data": body},
        )
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
