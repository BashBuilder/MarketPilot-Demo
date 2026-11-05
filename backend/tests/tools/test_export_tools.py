"""Export tool: approval gate, file assembly and Reviewer-only permissions."""

import hashlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.errors import GuardrailViolation, ToolError
from app.database.models import ApprovalDecision, Asset, AssetKind, Base
from app.database.repositories import approvals, campaigns, runs, versions
from app.harness.registry import ToolRegistry
from app.tools.export_models import ExportPackageArgs
from app.tools.export_tools import EXPORT_TOOL_NAME, export_package, register_export_tools

PACKAGE = {
    "brief": {"product": "hair care", "goal": "awareness"},
    "copy": {"variants": [{"channel": "social", "headline": "Care that shows"}]},
    "score": {"total": 82.0, "dimensions": []},
}


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


async def make_version(
    session_factory: async_sessionmaker[AsyncSession],
    asset_dir: Path,
    *,
    decision: ApprovalDecision | None,
) -> tuple[UUID, Path, str]:
    data = b"\x89PNG\r\n\x1a\n" + b"fake image bytes"
    source = asset_dir / "source.png"
    source.write_bytes(data)
    checksum = hashlib.sha256(data).hexdigest()

    async with session_factory() as session:
        campaign = await campaigns.create(session, idea="Export test")
        run = await runs.create(session, campaign_id=campaign.id)
        version = await versions.create(
            session,
            campaign_id=campaign.id,
            package=PACKAGE,
            score=82.0,
        )
        session.add(
            Asset(
                campaign_version_id=version.id,
                kind=AssetKind.IMAGE,
                uri=source.name,
                checksum=checksum,
                model="fake",
                seed=7,
                prompt="source product shot",
                media_type="image/png",
            )
        )
        if decision is not None:
            await approvals.create(
                session,
                run_id=run.id,
                campaign_version_id=version.id,
                decision=decision,
            )
        await session.commit()
        return version.id, source, checksum


@pytest.mark.parametrize("decision", [None, ApprovalDecision.REVISE])
async def test_export_refused_without_approval(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    decision: ApprovalDecision | None,
) -> None:
    version_id, _, _ = await make_version(session_factory, tmp_path, decision=decision)

    with pytest.raises(GuardrailViolation, match="no approval"):
        await export_package(version_id, session_factory=session_factory, asset_dir=tmp_path)

    assert not (tmp_path / "exports").exists()


async def test_approved_version_exports_package_and_assets(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    version_id, source, checksum = await make_version(
        session_factory, tmp_path, decision=ApprovalDecision.APPROVE
    )

    result = await export_package(version_id, session_factory=session_factory, asset_dir=tmp_path)

    assert result.folder == tmp_path / "exports" / str(version_id)
    assert result.package_path.is_file()
    data = json.loads(result.package_path.read_text(encoding="utf-8"))
    assert data["brief"] == PACKAGE["brief"]
    assert data["copy"] == PACKAGE["copy"]
    assert data["score"] == PACKAGE["score"]
    assert data["version"]["id"] == str(version_id)
    assert data["version"]["number"] == 1
    assert len(result.asset_paths) == 1
    assert result.asset_paths[0].read_bytes() == source.read_bytes()
    exported = data["assets"][0]
    assert exported["file"] == result.asset_paths[0].name
    assert exported["checksum"] == checksum
    assert exported["model"] == "fake"


async def test_registry_limits_export_to_reviewer(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    version_id, _, _ = await make_version(
        session_factory, tmp_path, decision=ApprovalDecision.APPROVE
    )
    registry = ToolRegistry()
    register_export_tools(registry, session_factory=session_factory, asset_dir=tmp_path)

    exported = await registry.get_tool("reviewer", EXPORT_TOOL_NAME).run(
        ExportPackageArgs(version_id=version_id)
    )
    assert exported.package_path.is_file()

    for agent in ("brief", "research", "copywriter", "creative_director", "designer", "compliance"):
        with pytest.raises(GuardrailViolation, match="may not use"):
            registry.get_tool(agent, EXPORT_TOOL_NAME)  # type: ignore[arg-type]


async def test_missing_version_is_a_tool_error(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    with pytest.raises(ToolError, match="not found"):
        await export_package(uuid4(), session_factory=session_factory, asset_dir=tmp_path)
