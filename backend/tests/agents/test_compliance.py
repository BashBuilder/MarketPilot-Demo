"""Compliance Agent: policy-backed flags without rewriting copy."""

from typing import Any
from uuid import UUID

from copywriter_data import BRIEF, CURRENT_COPY, IDEA
from fake_llm import FakeLLMClient
from reviewer_support import FakePolicy, audit_rows, make_tools, settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.compliance import ComplianceAgent
from app.agents.outputs import AdCopySet
from app.graph.state import WorkflowState

REPORT: dict[str, Any] = {
    "items": [
        {
            "check": "Guaranteed results",
            "passed": False,
            "reason": "The email description promises a guaranteed outcome.",
        },
        {
            "check": "Medical claims",
            "passed": True,
            "reason": "No medical or therapeutic claims were found.",
        },
    ]
}


def state() -> WorkflowState:
    return WorkflowState(
        idea=IDEA,
        brief=BRIEF,
        copy=AdCopySet.model_validate(CURRENT_COPY),
    )


async def test_compliance_flags_with_policy_context(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> None:
    policy = FakePolicy()
    tools = make_tools(session_factory, run_id, policy=policy, agent="compliance")
    fake = FakeLLMClient([REPORT])

    result = await ComplianceAgent().run(state(), fake, tools=tools, settings=settings())

    assert [item.passed for item in result.items] == [False, True]
    assert result.items[0].check == "Guaranteed results"
    assert len(policy.queries) == 1
    assert "HydraSilk Shampoo" in policy.queries[0].query
    policy_block = fake.requests[0].messages[2]["content"]
    assert '<untrusted source="tool-results">' in policy_block
    assert "Do not promise guaranteed results" in policy_block
    rows = await audit_rows(session_factory, run_id)
    assert [row.tool for row in rows] == ["policy_lookup"]
    assert rows[0].status == "success"
