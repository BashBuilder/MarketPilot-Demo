"""Shared fixtures for graph state and node tests."""

import os
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.agents.outputs import (
    AdCopySet,
    AssetSet,
    AudienceResearch,
    CampaignBrief,
    ComplianceReport,
    CreativeDirection,
    CreativeScore,
)
from app.database.models import Base
from app.database.repositories import campaigns, runs
from app.graph.state import WorkflowState


def _dimension(score: float) -> dict[str, object]:
    return {"score": score, "justification": "Clear rationale."}


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture()
async def run_id(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Graph node test campaign")
        run = await runs.create(session, campaign_id=campaign.id)
        await session.commit()
        return run.id


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database ending in '_test'")
    return url


@pytest.fixture()
async def pg_session_factory(
    test_database_url: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Real PostgreSQL with pgvector, truncated so each test starts clean."""
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(Base.metadata.create_all)
            tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
            await connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    except (OSError, OperationalError) as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable: {exc}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def full_state() -> WorkflowState:
    return WorkflowState(
        idea="Create an advertising campaign for a fictional hair-care product",
        brief=CampaignBrief(
            product="Aurelia Repair Shampoo",
            goal="Launch a repair line for adults",
            audience="Adults aged 25 to 40",
            tone="Warm and confident",
            channels=["Instagram"],
            constraints=["No medical claims"],
        ),
        research=AudienceResearch(
            segments=[{"name": "Professionals", "description": "Busy professionals."}],
            pain_points=["Frizz"],
            messaging_angles=["Repair without weight"],
            sources=[
                {
                    "url": "https://example.com/research/hair-care-trends",
                    "title": "Hair care trends: scalp-first routines",
                }
            ],
        ),
        copy=AdCopySet(
            variants=[
                {
                    "channel": "Instagram",
                    "headline": "Repair starts here",
                    "description": "A weekly ritual for colour-treated hair.",
                    "cta": "Shop now",
                }
            ]
        ),
        direction=CreativeDirection(
            image_prompts=["Soft-lit studio portrait"],
            video_prompts=["Slow dolly shot"],
            style_guide="Warm neutrals and editorial calm",
            composition="Rule of thirds with open space",
            negative_prompts=["watermark"],
        ),
        assets=AssetSet(
            assets=[
                {
                    "uri": "s3://bucket/hero.png",
                    "checksum": "a" * 64,
                    "model": "flux",
                    "seed": 1,
                    "prompt": "Editorial portrait",
                }
            ]
        ),
        compliance=ComplianceReport(
            items=[
                {
                    "check": "Medical claims",
                    "passed": True,
                    "reason": "No claims found.",
                }
            ]
        ),
        score=CreativeScore(
            brief_alignment=_dimension(8),
            audience_fit=_dimension(7),
            copy_quality=_dimension(9),
            visual_quality=_dimension(8),
            compliance_risk=_dimension(6),
            total=76.0,
        ),
        versions=[1, 2],
        status="awaiting_approval",
        retry_counters={"research": 1},
        errors=["copy retried once"],
    )
