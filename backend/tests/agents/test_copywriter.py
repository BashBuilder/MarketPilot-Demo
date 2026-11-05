"""Copywriter Agent: normal generation and flag-only revision."""

from uuid import UUID

from copywriter_data import CHANGED_UNFLAGGED, CURRENT_COPY, REVISED_COPY
from copywriter_support import (
    FakePolicy,
    make_tools,
    normal_state,
    revision_state,
    settings,
)
from fake_llm import FakeLLMClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.copywriter import CopywriterAgent


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


async def test_normal_run_generates_copy_with_policy_context(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    policy = FakePolicy()
    tools = make_tools(session_factory, run_id, policy=policy)
    fake = FakeLLMClient([CURRENT_COPY])

    result = await CopywriterAgent().run(normal_state(), fake, tools=tools, settings=settings())

    assert len(result.variants) == 3
    assert len(policy.queries) == 1
    state_block = fake.requests[0].messages[1]["content"]
    assert "Launch a campaign for colour-treated hair" in state_block
    assert "Repair without weighing hair down" in state_block
    policy_block = fake.requests[0].messages[2]["content"]
    assert "Do not promise guaranteed results" in policy_block


async def test_revision_changes_only_the_flagged_variant(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    previous = revision_state().copy
    assert previous is not None
    tools = make_tools(session_factory, run_id, policy=FakePolicy())
    fake = FakeLLMClient([REVISED_COPY])

    result = await CopywriterAgent().run(revision_state(), fake, tools=tools, settings=settings())

    assert result.variants[0] == previous.variants[0]
    assert result.variants[1] != previous.variants[1]
    assert result.variants[2] == previous.variants[2]
    revision_block = fake.requests[0].messages[1]["content"]
    assert "guaranteed results" in revision_block
    assert "Your hair, softer" in revision_block
    assert "Launch a campaign for colour-treated hair" not in revision_block
    assert "Repair without weighing hair down" not in revision_block


async def test_revision_rejects_changes_to_unflagged_variants(
    session_factory: async_sessionmaker[AsyncSession], run_id: UUID
) -> None:
    tools = make_tools(session_factory, run_id, policy=FakePolicy())
    fake = FakeLLMClient([CHANGED_UNFLAGGED, REVISED_COPY])
    sleeps = SleepRecorder()

    result = await CopywriterAgent().run(
        revision_state(),
        fake,
        tools=tools,
        settings=settings(retry_max_attempts=2),
        sleep=sleeps,
        jitter=lambda: 0.0,
    )

    assert result.variants[0].headline == "Repair starts here"
    assert len(fake.requests) == 2
    assert sleeps.delays == [0.5]
    feedback = fake.requests[1].messages[-1]["content"]
    assert "variant 1 (Instagram) is not flagged but was changed" in feedback
    assert "keep it identical" in feedback
