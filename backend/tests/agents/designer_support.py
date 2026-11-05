"""Shared fixtures for Designer Agent tests."""

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.outputs import AssetSet, ComplianceReport, CreativeDirection
from app.core.config import Settings
from app.database.models import ToolCall
from app.graph.state import WorkflowState
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import AgentName, ToolRegistry
from app.tools.image_tools import FakeImageGenerator, register_image_tools

IDEA = "Create a campaign for a fictional hair-care product"

IMAGE_PROMPTS = (
    "Soft-lit studio portrait with glossy, natural hair",
    "Sunlit bathroom shelf with the shampoo bottle",
)

DIRECTION = {
    "image_prompts": list(IMAGE_PROMPTS),
    "video_prompts": ["Slow dolly shot through a sunlit bathroom"],
    "style_guide": "Warm neutrals, editorial calm, no plastic textures",
    "composition": "Rule of thirds with generous negative space on the right",
    "negative_prompts": ["text", "watermark"],
}


def settings(asset_dir: Path, **overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        asset_dir=asset_dir,
        **overrides,
    )


def direction() -> CreativeDirection:
    return CreativeDirection.model_validate(DIRECTION)


def state(
    *,
    assets: AssetSet | None = None,
    compliance: ComplianceReport | None = None,
) -> WorkflowState:
    return WorkflowState(
        idea=IDEA,
        direction=direction(),
        assets=assets,
        compliance=compliance,
    )


def make_tools(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    asset_dir: Path,
    *,
    agent: AgentName = "designer",
    tool_settings: Settings | None = None,
) -> ToolCallMiddleware:
    registry = ToolRegistry()
    register_image_tools(registry, FakeImageGenerator(asset_dir))
    return ToolCallMiddleware(
        registry=registry,
        guardrails=RunGuardrails(tool_settings or settings(asset_dir)),
        session_factory=factory,
        run_id=run_id,
        agent=agent,
    )


async def audit_rows(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> list[ToolCall]:
    async with factory() as session:
        result = await session.scalars(select(ToolCall).where(ToolCall.run_id == run_id))
        return list(result)
