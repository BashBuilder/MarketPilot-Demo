"""Typed arguments and results for package export."""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExportPackageArgs(BaseModel):
    """Validated arguments for ``export_package``."""

    model_config = ConfigDict(extra="forbid")

    version_id: UUID


class ExportResult(BaseModel):
    """Paths written by one export; the JSON file references the assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version_id: UUID
    version: int
    folder: Path
    package_path: Path
    asset_paths: list[Path]
