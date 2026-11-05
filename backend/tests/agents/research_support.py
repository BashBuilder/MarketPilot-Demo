"""Shared fixtures for Research Agent tests."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.database.models import ToolCall
from app.graph.state import WorkflowState
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import AgentName, ToolRegistry
from app.tools.search_tools import FakeSearchProvider, register_search_tools

IDEA = "Create a campaign for a fictional hair-care product"

VALID_RESEARCH: dict[str, Any] = {
    "segments": [
        {
            "name": "Colour-treated professionals",
            "description": "Busy professionals who colour their hair monthly.",
        }
    ],
    "pain_points": ["Frizz after washing"],
    "messaging_angles": ["Repair without weighing hair down"],
    "sources": [
        {
            "url": "https://example.com/research/hair-care-trends",
            "title": "Hair care trends: scalp-first routines",
        },
        {
            "url": "https://example.com/research/audience-messaging",
            "title": "Audience messaging for everyday personal care",
        },
    ],
}

INVENTED_RESEARCH = {
    **VALID_RESEARCH,
    "sources": [{"url": "https://invented.example/claim", "title": "Invented claim"}],
}


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        **overrides,
    )


def state() -> WorkflowState:
    return WorkflowState(idea=IDEA)


def make_tools(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    *,
    agent: AgentName = "research",
    tool_settings: Settings | None = None,
) -> ToolCallMiddleware:
    registry = ToolRegistry()
    register_search_tools(registry, FakeSearchProvider())
    return ToolCallMiddleware(
        registry=registry,
        guardrails=RunGuardrails(tool_settings or settings()),
        session_factory=factory,
        run_id=run_id,
        agent=agent,
    )


async def audit_rows(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> list[ToolCall]:
    async with factory() as session:
        result = await session.scalars(select(ToolCall).where(ToolCall.run_id == run_id))
        return list(result)
