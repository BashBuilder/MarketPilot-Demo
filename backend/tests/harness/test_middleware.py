"""Every tool call outcome must leave exactly one audit row."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from support import (
    boom,
    echo,
    make_middleware,
    make_run,
    rows_for,
    settings,
)

from app.core.errors import GuardrailViolation, ToolError


async def test_successful_call_writes_one_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await make_run(session_factory)
    middleware = make_middleware(
        session_factory,
        run_id,
        agent="research",
        tool="search_tools",
        implementation=echo,
        tool_settings=settings(),
    )

    assert await middleware.call("search_tools", {"text": "hi"}) == "hi"

    rows = await rows_for(session_factory, run_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.run_id == run_id
    assert row.agent == "research"
    assert row.tool == "search_tools"
    assert row.status == "success"
    assert len(row.args_hash) == 64
    assert row.duration_ms >= 0
    assert row.error is None


async def test_denied_call_writes_denied_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await make_run(session_factory)
    middleware = make_middleware(
        session_factory,
        run_id,
        agent="copywriter",
        tool="search_tools",
        implementation=echo,
        tool_settings=settings(),
    )

    with pytest.raises(GuardrailViolation, match="may not use"):
        await middleware.call("search_tools", {"text": "hi"})

    rows = await rows_for(session_factory, run_id)
    assert len(rows) == 1
    assert rows[0].status == "denied"
    assert "may not use" in (rows[0].error or "")
    assert rows[0].cost is None


async def test_exhausted_cap_writes_denied_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await make_run(session_factory)
    middleware = make_middleware(
        session_factory,
        run_id,
        agent="designer",
        tool="generate_image",
        implementation=echo,
        tool_settings=settings(max_image_calls_per_run=0),
    )

    with pytest.raises(GuardrailViolation, match="image cap of 0"):
        await middleware.call("generate_image", {"text": "hero"})

    rows = await rows_for(session_factory, run_id)
    assert [row.status for row in rows] == ["denied"]
    assert rows[0].tool == "generate_image"


async def test_failing_call_writes_failed_row_and_reraises(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await make_run(session_factory)
    middleware = make_middleware(
        session_factory,
        run_id,
        agent="research",
        tool="search_tools",
        implementation=boom,
        tool_settings=settings(),
    )

    with pytest.raises(ToolError, match="boom"):
        await middleware.call("search_tools", {"text": "hi"})

    rows = await rows_for(session_factory, run_id)
    assert len(rows) == 1
    assert rows[0].status == "error"
    assert rows[0].error == "boom"
