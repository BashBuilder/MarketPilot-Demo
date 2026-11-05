"""Shared fixtures for Reviewer Agent tests."""

from typing import Any
from uuid import UUID

from copywriter_data import BRIEF, COMPLIANCE, CURRENT_COPY, IDEA, POLICY_MATCH, RESEARCH
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.outputs import AdCopySet
from app.core.config import Settings
from app.database.models import ToolCall
from app.graph.state import WorkflowState
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import AgentName, ToolRegistry, ToolSpec
from app.tools.policy_models import PolicyLookupArgs, PolicyMatch
from app.tools.policy_tools import POLICY_TOOL_NAME

SCORE: dict[str, Any] = {
    "brief_alignment": {
        "score": 8,
        "justification": "Follows the brief closely.",
    },
    "audience_fit": {
        "score": 7,
        "justification": "Speaks to colour-treated hair.",
    },
    "copy_quality": {
        "score": 9,
        "justification": "Clear, specific and persuasive.",
    },
    "visual_quality": {
        "score": 8,
        "justification": "Consistent with the warm art direction.",
    },
    "compliance_risk": {
        "score": 6,
        "justification": "One claim needs softer wording.",
    },
    "total": 76.0,
}

MISMATCHED_SCORE = {**SCORE, "total": 90.0}


class FakePolicy:
    def __init__(self) -> None:
        self.queries: list[PolicyLookupArgs] = []

    async def __call__(self, args: PolicyLookupArgs) -> list[PolicyMatch]:
        self.queries.append(args)
        return [POLICY_MATCH]


def make_registry(policy: FakePolicy) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_tool(ToolSpec(name=POLICY_TOOL_NAME, args_model=PolicyLookupArgs, run=policy))
    return registry


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        **overrides,
    )


def make_tools(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    *,
    policy: FakePolicy,
    agent: AgentName = "reviewer",
    tool_settings: Settings | None = None,
) -> ToolCallMiddleware:
    return ToolCallMiddleware(
        registry=make_registry(policy),
        guardrails=RunGuardrails(tool_settings or settings()),
        session_factory=factory,
        run_id=run_id,
        agent=agent,
    )


def review_state() -> WorkflowState:
    return WorkflowState(
        idea=IDEA,
        brief=BRIEF,
        research=RESEARCH,
        copy=AdCopySet.model_validate(CURRENT_COPY),
        compliance=COMPLIANCE,
    )


async def audit_rows(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> list[ToolCall]:
    async with factory() as session:
        result = await session.scalars(select(ToolCall).where(ToolCall.run_id == run_id))
        return list(result)
