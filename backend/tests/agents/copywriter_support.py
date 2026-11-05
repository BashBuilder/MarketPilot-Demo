"""Shared middleware fixtures for Copywriter Agent tests."""

from uuid import UUID

from copywriter_data import BRIEF, COMPLIANCE, CURRENT_COPY, IDEA, POLICY_MATCH, RESEARCH
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.outputs import AdCopySet
from app.core.config import Settings
from app.graph.state import WorkflowState
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import AgentName, ToolRegistry, ToolSpec
from app.tools.image_models import GenerateImageArgs
from app.tools.policy_models import PolicyLookupArgs, PolicyMatch
from app.tools.policy_tools import POLICY_TOOL_NAME


class FakePolicy:
    def __init__(self) -> None:
        self.queries: list[PolicyLookupArgs] = []

    async def __call__(self, args: PolicyLookupArgs) -> list[PolicyMatch]:
        self.queries.append(args)
        return [POLICY_MATCH]


async def _noop_image(args: GenerateImageArgs) -> None:
    del args


def make_registry(policy: FakePolicy) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_tool(ToolSpec(name=POLICY_TOOL_NAME, args_model=PolicyLookupArgs, run=policy))
    registry.register_tool(
        ToolSpec(name="generate_image", args_model=GenerateImageArgs, run=_noop_image)
    )
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
    agent: AgentName = "copywriter",
) -> ToolCallMiddleware:
    return ToolCallMiddleware(
        registry=make_registry(policy),
        guardrails=RunGuardrails(settings()),
        session_factory=factory,
        run_id=run_id,
        agent=agent,
    )


def normal_state() -> WorkflowState:
    return WorkflowState(idea=IDEA, brief=BRIEF, research=RESEARCH)


def revision_state() -> WorkflowState:
    return WorkflowState(
        idea=IDEA,
        brief=BRIEF,
        research=RESEARCH,
        copy=AdCopySet.model_validate(CURRENT_COPY),
        compliance=COMPLIANCE,
    )
