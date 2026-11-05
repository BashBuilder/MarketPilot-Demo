"""Export an approved campaign version and the asset files it references."""

from functools import partial
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import GuardrailViolation, ToolError
from app.database.models import Approval, ApprovalDecision, Asset, CampaignVersion
from app.harness.registry import ToolRegistry, ToolSpec
from app.tools.export_files import copy_asset, write_package
from app.tools.export_models import ExportPackageArgs, ExportResult

EXPORT_TOOL_NAME = "export_package"


async def export_package(
    version_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    asset_dir: Path,
) -> ExportResult:
    """Write an approved package and its assets under ``asset_dir/exports``."""
    async with session_factory() as session:
        version = await session.get(CampaignVersion, version_id)
        if version is None:
            raise ToolError(
                f"campaign version not found: {version_id}",
                details={"version_id": str(version_id)},
            )

        approved = await session.scalar(
            select(Approval.id)
            .where(
                Approval.campaign_version_id == version_id,
                Approval.decision == ApprovalDecision.APPROVE,
            )
            .limit(1)
        )
        if approved is None:
            raise GuardrailViolation(
                f"version {version_id} has no approval",
                details={"version_id": str(version_id)},
            )

        assets = (
            await session.scalars(
                select(Asset)
                .where(Asset.campaign_version_id == version_id)
                .order_by(Asset.created_at.asc())
            )
        ).all()
        package = dict(version.package)
        version_number = version.version
        campaign_id = version.campaign_id
        version_score = version.score

    asset_root = asset_dir.resolve()
    folder = asset_root / "exports" / str(version_id)
    folder.mkdir(parents=True, exist_ok=True)

    exported_assets: list[dict[str, object]] = []
    asset_paths: list[Path] = []
    for asset in assets:
        destination, metadata = copy_asset(asset, asset_root, folder)
        asset_paths.append(destination)
        exported_assets.append(metadata)

    package["version"] = {
        "id": str(version_id),
        "number": version_number,
        "campaign_id": str(campaign_id),
        "score": version_score,
    }
    package["assets"] = exported_assets

    package_path = write_package(package, folder)

    return ExportResult(
        version_id=version_id,
        version=version_number,
        folder=folder,
        package_path=package_path,
        asset_paths=asset_paths,
    )


async def _run_export(
    args: ExportPackageArgs,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    asset_dir: Path,
) -> ExportResult:
    return await export_package(
        args.version_id,
        session_factory=session_factory,
        asset_dir=asset_dir,
    )


def register_export_tools(
    registry: ToolRegistry,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    asset_dir: Path,
) -> None:
    """Register export; the allowlist still limits it to Reviewer."""
    registry.register_tool(
        ToolSpec(
            name=EXPORT_TOOL_NAME,
            args_model=ExportPackageArgs,
            run=partial(_run_export, session_factory=session_factory, asset_dir=asset_dir),
            side_effecting=True,
        )
    )
