"""Filesystem helpers for exporting approved campaign packages."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from app.core.errors import ToolError
from app.database.models import Asset


def copy_asset(asset: Asset, asset_root: Path, folder: Path) -> tuple[Path, dict[str, object]]:
    """Copy one verified asset and return its path and JSON metadata."""
    source = _resolve_asset(asset, asset_root)
    _verify_checksum(asset, source)
    destination = folder / f"{asset.id}{source.suffix.lower()}"
    try:
        shutil.copyfile(source, destination)
    except OSError as exc:
        raise ToolError(
            f"could not copy asset: {asset.uri}",
            details={"uri": asset.uri, "path": str(destination)},
        ) from exc
    return destination, {
        "id": str(asset.id),
        "kind": asset.kind.value,
        "file": destination.name,
        "uri": asset.uri,
        "checksum": asset.checksum,
        "model": asset.model,
        "seed": asset.seed,
        "prompt": asset.prompt,
        "media_type": asset.media_type,
    }


def write_package(package: dict[str, Any], folder: Path) -> Path:
    """Write stable, human-readable JSON for the exported package."""
    path = folder / "package.json"
    try:
        path.write_text(
            json.dumps(package, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ToolError(
            "could not write exported package",
            details={"path": str(path)},
        ) from exc
    return path


def _resolve_asset(asset: Asset, asset_root: Path) -> Path:
    """Resolve a local asset URI and keep reads inside the asset directory."""
    uri = asset.uri
    if uri.startswith("file://"):
        candidate = Path(uri.removeprefix("file://"))
    elif "://" in uri:
        raise ToolError("unsupported asset URI scheme", details={"uri": uri})
    else:
        candidate = Path(uri)
        if not candidate.is_absolute():
            candidate = asset_root / candidate

    resolved = candidate.resolve()
    if not resolved.is_relative_to(asset_root):
        raise ToolError("asset path escapes the asset directory", details={"uri": uri})
    if not resolved.is_file():
        raise ToolError(f"asset file not found: {uri}", details={"uri": uri})
    return resolved


def _verify_checksum(asset: Asset, path: Path) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ToolError(f"could not read asset: {asset.uri}", details={"uri": asset.uri}) from exc
    if hashlib.sha256(data).hexdigest() != asset.checksum.lower():
        raise ToolError("asset checksum mismatch", details={"uri": asset.uri})
