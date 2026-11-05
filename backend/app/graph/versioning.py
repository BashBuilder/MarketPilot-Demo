"""Immutable campaign version snapshots taken at the human approval gate.

Version numbers are append-only: each snapshot asks the repository to append the
next number and links it to the previous snapshot as its parent. No repository
function may rewrite a version after it is written.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CampaignVersion
from app.database.repositories import runs, versions
from app.graph.state import WorkflowState

PACKAGE_FIELDS: tuple[str, ...] = (
    "brief",
    "research",
    "copy",
    "direction",
    "assets",
    "compliance",
    "score",
)


def package_payload(state: WorkflowState) -> dict[str, Any]:
    """Serialize the seven package sections exactly as the API contract expects."""
    payload: dict[str, Any] = {}
    for field in PACKAGE_FIELDS:
        value = getattr(state, field)
        payload[field] = value.model_dump(mode="json") if value is not None else None
    return payload


async def snapshot_package(
    session: AsyncSession,
    run_id: UUID,
    state: WorkflowState,
) -> CampaignVersion:
    """Append ``state`` as the campaign's next immutable version.

    The repository assigns ``version = previous + 1``. The parent is the
    previously latest version, or ``None`` for the campaign's first package.
    """
    run = await runs.get(session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    latest = await versions.get_latest(session, run.campaign_id)
    return await versions.create(
        session,
        campaign_id=run.campaign_id,
        package=package_payload(state),
        parent_version_id=latest.id if latest is not None else None,
        score=state.score.total if state.score is not None else None,
    )
