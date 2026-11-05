"""Research Agent: grounded citations and retry feedback."""

from uuid import UUID

from fake_llm import FakeLLMClient
from research_support import (
    INVENTED_RESEARCH,
    VALID_RESEARCH,
    SleepRecorder,
    audit_rows,
    make_tools,
    settings,
    state,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.research import ResearchAgent


async def test_valid_cited_output_passes(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    tools = make_tools(session_factory, run_id)
    fake = FakeLLMClient([VALID_RESEARCH])

    result = await ResearchAgent().run(state(), fake, tools=tools, settings=settings())

    assert str(result.sources[0].url) == "https://example.com/research/hair-care-trends"
    assert len(fake.requests) == 1
    tool_block = fake.requests[0].messages[2]["content"]
    assert '<untrusted source="tool-results">' in tool_block
    assert "hair-care-trends" in tool_block
    rows = await audit_rows(session_factory, run_id)
    assert [row.status for row in rows] == ["success"]


async def test_invented_url_triggers_a_retry_with_the_url_in_feedback(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    tools = make_tools(session_factory, run_id)
    fake = FakeLLMClient([INVENTED_RESEARCH, VALID_RESEARCH])
    sleeps = SleepRecorder()

    result = await ResearchAgent().run(
        state(),
        fake,
        tools=tools,
        settings=settings(retry_max_attempts=2),
        sleep=sleeps,
        jitter=lambda: 0.0,
    )

    assert str(result.sources[0].url) == "https://example.com/research/hair-care-trends"
    assert len(fake.requests) == 2
    assert sleeps.delays == [0.5]
    feedback = fake.requests[1].messages[-1]["content"]
    assert "https://invented.example/claim" in feedback
    assert "was not retrieved by the search tool" in feedback
    assert len(await audit_rows(session_factory, run_id)) == 1
