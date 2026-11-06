"""Mapping helpers for the Designer agent's asset generation and revisions."""

import hashlib
import re
from collections.abc import Sequence
from pathlib import Path

from app.agents.outputs import Asset, ComplianceItem
from app.tools.asset_storage import relative_uri
from app.tools.image_models import GeneratedImage, seed_from_digest

_ASSET_INDEX = re.compile(r"(?:assets?|images?)\s+#?(\d+)", re.IGNORECASE)
_ASSET_WORD = re.compile(r"\b(?:assets?|images?)\b", re.IGNORECASE)
_MAX_INSTRUCTION = 2000


def to_asset(image: GeneratedImage, asset_dir: Path) -> Asset:
    """Record the published URI when storage assigned one, else the local path."""
    return Asset(
        uri=image.uri or asset_uri(image.path, asset_dir),
        checksum=image.checksum,
        model=image.model,
        seed=image.seed,
        prompt=image.prompt,
    )


def asset_uri(path: Path, asset_dir: Path) -> str:
    """Prefer a portable relative URI so verification resolves under asset_dir."""
    return relative_uri(path, asset_dir)


def seed_for(prompt: str, index: int) -> int:
    """Derive a stable seed so regenerating the same direction is idempotent."""
    digest = hashlib.sha256(f"{index}:{prompt}".encode()).digest()
    return seed_from_digest(digest)


def flagged_indices(
    failed: Sequence[ComplianceItem],
    assets: Sequence[Asset],
) -> frozenset[int]:
    """Return 1-based indexes of assets a failed compliance item names."""
    if not failed:
        return frozenset()
    found: set[int] = set()
    global_failure = False
    for item in failed:
        text = f"{item.check} {item.reason}"
        explicit = {int(match) for match in _ASSET_INDEX.findall(text)}
        explicit.update(
            number for number, asset in enumerate(assets, start=1) if _names_uri(text, asset)
        )
        if explicit:
            found.update(explicit)
        elif _ASSET_WORD.search(text):
            global_failure = True
    in_range = {number for number in found if 1 <= number <= len(assets)}
    if in_range:
        return frozenset(in_range)
    # A failure that names assets generally is global; allow all to change.
    return frozenset(range(1, len(assets) + 1)) if global_failure else frozenset()


def _names_uri(text: str, asset: Asset) -> bool:
    lowered = text.casefold()
    names = {asset.uri.casefold(), Path(asset.uri).name.casefold()}
    return any(name and name in lowered for name in names)


def mentions_asset(text: str, asset: Asset, number: int) -> bool:
    if _names_uri(text, asset):
        return True
    return any(int(match) == number for match in _ASSET_INDEX.findall(text))


def revision_instruction(
    failed: Sequence[ComplianceItem],
    asset: Asset,
    number: int,
) -> str:
    reasons = [
        item.reason
        for item in failed
        if mentions_asset(f"{item.check} {item.reason}", asset, number)
    ]
    detail = "; ".join(dict.fromkeys(reason.strip() for reason in reasons if reason.strip()))
    text = (
        f"Revise this asset to pass compliance: {detail}"
        if detail
        else "Revise this asset to resolve the compliance findings"
    )
    return text[:_MAX_INSTRUCTION]
