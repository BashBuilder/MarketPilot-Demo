"""Test doubles and a sqlite session factory for harness tests."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ToolError
from app.database.models import ToolCall
from app.database.repositories import campaigns, runs
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import AgentName, ToolRegistry, ToolSpec


class EchoArgs(BaseModel):
    text: str


async def echo(args: EchoArgs) -> str:
    return args.text


async def boom(args: EchoArgs) -> str:
    raise ToolError("boom")


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        **overrides,
    )


async def make_run(factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with factory() as session:
        campaign = await campaigns.create(session, idea="Middleware test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id


def make_middleware(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    *,
    agent: AgentName,
    tool: str,
    implementation: Callable[[EchoArgs], Awaitable[str]],
    tool_settings: Settings,
) -> ToolCallMiddleware:
    registry = ToolRegistry()
    registry.register_tool(ToolSpec(name=tool, args_model=EchoArgs, run=implementation))
    return ToolCallMiddleware(
        registry=registry,
        guardrails=RunGuardrails(tool_settings),
        session_factory=factory,
        run_id=run_id,
        agent=agent,
        step="research",
    )


async def rows_for(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> list[ToolCall]:
    async with factory() as session:
        result = await session.scalars(select(ToolCall).where(ToolCall.run_id == run_id))
        return list(result)
