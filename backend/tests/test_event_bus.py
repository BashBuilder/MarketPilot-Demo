"""Event bus storage semantics: replay cursors and the Redis stream key."""

import json
from typing import Any
from uuid import uuid4

from app.events.bus import EventRecord, InMemoryEventBus, RedisEventBus


async def test_in_memory_replay_starts_strictly_after_the_cursor() -> None:
    bus = InMemoryEventBus()
    run_id = uuid4()

    ids = [
        await bus.publish(run_id, "agent_started", "brief", {"index": index}) for index in range(3)
    ]

    records = await bus.read(run_id, ids[0])
    assert [record.id for record in records] == ids[1:]
    assert await bus.read(uuid4(), None) == []


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
        self.ranges: list[tuple[str, str, str]] = []
        self.rows: list[tuple[str, dict[str, Any]]] = []
        self.closed = False

    async def xadd(self, key: str, fields: dict[str, Any]) -> str:
        self.added.append((key, fields))
        return "1700-0"

    async def xrange(self, key: str, *, min: str, max: str) -> list[tuple[str, dict[str, Any]]]:
        self.ranges.append((key, min, max))
        return list(self.rows)

    async def aclose(self) -> None:
        self.closed = True
