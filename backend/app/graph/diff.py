"""Field-level diffs between immutable campaign version snapshots.

The diff is deliberately a pure tree walk over the stored package, so it stays
independent of the database and of the seven package models. ``load_diff`` is
the only function here that touches persistence, and it only fetches the two
rows before delegating to ``compute_diff``.
"""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CampaignVersion
from app.database.repositories import versions

_MISSING = object()


def compute_diff(version_a: CampaignVersion, version_b: CampaignVersion) -> dict[str, Any]:
    """Return every leaf field that differs between two package snapshots."""
    return {
        "from": version_a.version,
        "to": version_b.version,
        "changes": _walk(version_a.package, version_b.package, ""),
    }


async def load_diff(
    session: AsyncSession,
    campaign_id: UUID,
    from_version: int,
    to_version: int,
) -> dict[str, Any]:
    """Fetch two versions for a campaign and return their field-level diff."""
    before = await versions.get(session, campaign_id, from_version)
    after = await versions.get(session, campaign_id, to_version)
    if before is None or after is None:
        missing = from_version if before is None else to_version
        raise ValueError(f"campaign version not found: {campaign_id} version {missing}")
    return compute_diff(before, after)


def _walk(before: Any, after: Any, path: str) -> list[dict[str, Any]]:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        return _walk_mapping(before, after, path)
    if isinstance(before, list) and isinstance(after, list):
        return _walk_list(before, after, path)
    if before != after:
        return [{"path": path, "before": _value(before), "after": _value(after)}]
    return []


def _walk_mapping(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    path: str,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for key in sorted(set(before) | set(after), key=str):
        child = f"{path}.{key}" if path else str(key)
        changes.extend(_walk(before.get(key, _MISSING), after.get(key, _MISSING), child))
    return changes


def _walk_list(before: list[Any], after: list[Any], path: str) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for index in range(max(len(before), len(after))):
        left = before[index] if index < len(before) else _MISSING
        right = after[index] if index < len(after) else _MISSING
        changes.extend(_walk(left, right, f"{path}.{index}"))
    return changes


def _value(value: Any) -> Any:
    return None if value is _MISSING else value
