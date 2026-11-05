"""Reviewer Agent: rubric retries, policy context and no approvals."""

from uuid import UUID

from fake_llm import FakeLLMClient
from reviewer_support import (
    MISMATCHED_SCORE,
    SCORE,
    FakePolicy,
    audit_rows,
    make_tools,
    review_state,
    settings,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.outputs import CreativeScore
from app.agents.reviewer import ReviewerAgent


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


async def test_reviewer_scores_with_policy_context(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> None:
    policy = FakePolicy()
    tools = make_tools(session_factory, run_id, policy=policy)
    fake = FakeLLMClient([SCORE])

    result = await ReviewerAgent().run(
        review_state(),
        fake,
        tools=tools,
        settings=settings(),
    )

    assert result.total == 76.0
    assert result.compliance_risk.score == 6
    assert len(policy.queries) == 1
    policy_block = fake.requests[0].messages[2]["content"]
    assert '<untrusted source="tool-results">' in policy_block
    assert "Do not promise guaranteed results" in policy_block
    rows = await audit_rows(session_factory, run_id)
    assert [row.tool for row in rows] == ["policy_lookup"]
    assert rows[0].status == "success"


async def test_total_mismatch_retries_with_feedback(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> None:
    policy = FakePolicy()
    tools = make_tools(session_factory, run_id, policy=policy)
    fake = FakeLLMClient([MISMATCHED_SCORE, SCORE])
    sleeps = SleepRecorder()

    result = await ReviewerAgent().run(
        review_state(),
        fake,
        tools=tools,
        settings=settings(retry_max_attempts=2),
        sleep=sleeps,
        jitter=lambda: 0.0,
    )

    assert result.total == 76.0
    assert len(fake.requests) == 2
    assert sleeps.delays == [0.5]
    feedback = fake.requests[1].messages[-1]["content"]
    assert "total must equal the weighted dimensions" in feedback
    assert len(policy.queries) == 1


def test_output_has_no_approval_field() -> None:
    payload = CreativeScore.model_validate(SCORE).model_dump()

    assert "approval" not in payload
    assert "approved" not in payload
