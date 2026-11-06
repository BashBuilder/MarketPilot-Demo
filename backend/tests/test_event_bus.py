"""Event bus storage semantics: replay cursors, stream caps and expiry."""

import json
from typing import Any
from uuid import uuid4

import pytest

from app.events.bus import InMemoryEventBus, RedisEventBus
from app.events.envelope import EventRecord


async def test_in_memory_replay_starts_strictly_after_the_cursor() -> None:
    bus = InMemoryEventBus()
    run_id = uuid4()

    ids = [
        await bus.publish(run_id, "agent_started", "brief", {"index": index}) for index in range(3)
    ]

    records = await bus.read(run_id, ids[0])
    assert [record.id for record in records] == ids[1:]
    assert await bus.read(uuid4(), None) == []


async def test_in_memory_bus_caps_each_run_stream() -> None:
    bus = InMemoryEventBus(maxlen=3)
    run_id = uuid4()

    ids = [
        await bus.publish(run_id, "agent_started", "brief", {"index": index}) for index in range(10)
    ]

    records = await bus.read(run_id, None)
    assert [record.id for record in records] == ids[-3:]
    assert len(records) == 3


async def test_redis_bus_caps_and_expires_after_a_terminal_event() -> None:
    client = FakeRedis()
    bus = RedisEventBus(client, maxlen=5, ttl_seconds=60)  # type: ignore[arg-type]
    run_id = uuid4()

    await bus.publish(run_id, "agent_started", "brief", {})
    assert client.limits == [(5, True)]
    assert client.expires == []

    await bus.publish(run_id, "awaiting_approval", "human", {"version": 1})
    assert client.expires == [(f"run:{run_id}:events", 60)]


@pytest.mark.parametrize(
    ("event_type", "data"),
    [
        ("completed", {"version": 1, "score": 80}),
        ("error", {"message": "boom", "recoverable": False}),
    ],
)
async def test_redis_bus_expires_after_other_terminal_events(
    event_type: str,
    data: dict[str, Any],
) -> None:
    client = FakeRedis()
    bus = RedisEventBus(client, ttl_seconds=30)  # type: ignore[arg-type]
    run_id = uuid4()

    await bus.publish(run_id, event_type, "human", data)

    assert client.expires == [(f"run:{run_id}:events", 30)]


async def test_redis_bus_does_not_expire_after_a_non_terminal_event() -> None:
    client = FakeRedis()
    bus = RedisEventBus(client)  # type: ignore[arg-type]

    await bus.publish(uuid4(), "error", "brief", {"message": "retry", "recoverable": True})

    assert client.expires == []


async def test_redis_bus_uses_one_stream_per_run_and_exclusive_range() -> None:
    client = FakeRedis()
    bus = RedisEventBus(client)  # type: ignore[arg-type]
    run_id = uuid4()

    event_id = await bus.publish(
        run_id,
        "tool_called",
        "research",
        {"tool": "search_tools", "duration_ms": 3, "status": "success"},
    )

    key, fields = client.added[0]
    assert event_id == "1700-0"
    assert key == f"run:{run_id}:events"
    assert fields["event"] == "tool_called"
    body = json.loads(fields["data"])
    assert body["run_id"] == str(run_id)
    assert body["agent"] == "research"
    assert body["tool"] == "search_tools"
    assert "timestamp" in body

    client.rows = [("1700-0", fields)]
    records = await bus.read(run_id, "1600-0")
    assert client.ranges == [(key, "(1600-0", "+")]
    assert records == [EventRecord(id="1700-0", event="tool_called", data=body)]


class FakeRedis:
    """Capture commands and return scripted XRANGE rows."""

    def __init__(self) -> None:
        self.added: list[tuple[str, dict[str, Any]]] = []
        self.limits: list[tuple[int | None, bool]] = []
        self.expires: list[tuple[str, int]] = []
        self.ranges: list[tuple[str, str, str]] = []
        self.rows: list[tuple[str, dict[str, Any]]] = []
        self.closed = False

    async def xadd(
        self,
        key: str,
        fields: dict[str, Any],
        *,
        maxlen: int | None = None,
        approximate: bool = False,
    ) -> str:
        self.added.append((key, fields))
        self.limits.append((maxlen, approximate))
        return "1700-0"

    async def xrange(self, key: str, *, min: str, max: str) -> list[tuple[str, dict[str, Any]]]:
        self.ranges.append((key, min, max))
        return list(self.rows)

    async def expire(self, key: str, ttl: int) -> bool:
        self.expires.append((key, ttl))
        return True

    async def aclose(self) -> None:
        self.closed = True
