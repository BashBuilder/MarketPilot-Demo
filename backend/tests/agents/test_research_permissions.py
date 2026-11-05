"""Research Agent: per-run search cap and Research-only permission."""

from uuid import UUID

import pytest
from fake_llm import FakeLLMClient
from research_support import VALID_RESEARCH, make_tools, settings, state
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.research import ResearchAgent
from app.core.errors import GuardrailViolation
from app.tools.search_tools import SEARCH_TOOL_NAME


async def test_search_call_cap_is_respected(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    tools = make_tools(
        session_factory,
        run_id,
        tool_settings=settings(max_search_calls_per_run=1),
    )
    fake = FakeLLMClient([VALID_RESEARCH])
    agent = ResearchAgent()

    await agent.run(state(), fake, tools=tools, settings=settings())

    with pytest.raises(GuardrailViolation, match="search cap of 1"):
        await agent.run(state(), fake, tools=tools, settings=settings())
    assert len(fake.requests) == 1


async def test_non_research_agent_cannot_call_search(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    tools = make_tools(session_factory, run_id, agent="brief")

    with pytest.raises(GuardrailViolation, match="may not use"):
        await tools.call(SEARCH_TOOL_NAME, {"query": "hair care audience"})
