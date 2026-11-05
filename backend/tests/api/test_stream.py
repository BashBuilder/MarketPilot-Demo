"""SSE replay, resume and terminal-close behavior."""

import json
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.repositories import campaigns, runs
from app.events.bus import InMemoryEventBus


async def test_stream_replays_and_ends_after_awaiting_approval(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
) -> None:
    run_id = await _make_run(session_factory)
    await event_bus.publish(run_id, "agent_started", "brief", {})
    await event_bus.publish(run_id, "awaiting_approval", "human", {"version": 1})

    response = await client.get(f"/api/v1/runs/{run_id}/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(response.text)
    assert [event["event"] for event in events] == ["agent_started", "awaiting_approval"]
    assert all(event["data"]["run_id"] == str(run_id) for event in events)
    assert events[-1]["data"]["version"] == 1


async def test_reconnect_after_third_event_receives_only_later_events(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
) -> None:
    run_id = await _make_run(session_factory)
    for index in range(5):
        await event_bus.publish(run_id, "agent_started", "brief", {"index": index})
    await event_bus.publish(run_id, "awaiting_approval", "human", {"version": 1})
    records = await event_bus.read(run_id, None)

    response = await client.get(
        f"/api/v1/runs/{run_id}/stream",
        headers={"Last-Event-ID": records[2].id},
    )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    expected_ids = [record.id for record in records[3:]]
    assert [event["id"] for event in events] == expected_ids
    assert len(set(event["id"] for event in events)) == len(events)
    assert all(event["data"]["run_id"] == str(run_id) for event in events)


async def test_unknown_run_returns_404_before_streaming(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/runs/{uuid4()}/stream")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def _make_run(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Stream test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id


def _parse_sse(text: str) -> list[dict[str, Any]]:
    """Parse SSE frames into id/event/data dicts, ignoring heartbeat comments."""
    events: list[dict[str, Any]] = []
    for block in text.strip().split("\n\n"):
        if not block or block.startswith(":"):
            continue
        frame: dict[str, Any] = {}
        for line in block.splitlines():
            field, _, value = line.partition(": ")
            if field == "data":
                frame["data"] = json.loads(value)
            elif field in {"id", "event"}:
                frame[field] = value
        if "event" in frame:
            events.append(frame)
    return events
