"""Human approval operations: record the decision, then continue the run.

The approval row is written first so every decision leaves an audit trail on the
version the human reviewed. Continuation is delegated to the workflow runner so
the graph, checkpointing and version snapshot stay in one place.
"""

from collections.abc import Mapping
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidRunState, ValidationFailure
from app.database.models import ApprovalDecision, CampaignVersion, RunStatus, WorkflowRun
from app.database.repositories import approvals as approvals_repo
from app.database.repositories import runs, versions
from app.graph.nodes import NodeAgent
from app.graph.workflow import (
    WorkflowDependencies,
    continue_run,
    resolve_revision_target,
)
from app.harness.checkpoints import load_latest_checkpoint
from app.harness.registry import AgentName


class ApprovalOutcome(BaseModel):
    """Response shape for a completed approval."""

    status: Literal["completed"] = "completed"
    version: int


class RevisionOutcome(BaseModel):
    """Response shape for a revision that continues in a new run."""

    run_id: UUID
    version: int


async def approve_run(
    run_id: UUID,
    comment: str | None = None,
    *,
    agents: Mapping[AgentName, NodeAgent],
    deps: WorkflowDependencies,
) -> ApprovalOutcome:
    """Record an approval and finish the run it belongs to."""
    run, version = await _awaiting_run(deps.session, run_id)
    clean_comment = _clean_comment(comment)
    await approvals_repo.create(
        deps.session,
        run_id=run_id,
        campaign_version_id=version.id,
        decision=ApprovalDecision.APPROVE,
        comment=clean_comment,
    )
    await continue_run(
        run_id,
        ApprovalDecision.APPROVE,
        agents=agents,
        deps=deps,
        comment=clean_comment,
        recorded=True,
    )
    return ApprovalOutcome(version=version.version)


async def revise_run(
    run_id: UUID,
    comment: str,
    target_node: str | None = None,
    *,
    agents: Mapping[AgentName, NodeAgent],
    deps: WorkflowDependencies,
) -> RevisionOutcome:
    """Record a revision and continue it in a new run from the target node."""
    clean_comment = _require_comment(comment)
    run, version = await _awaiting_run(deps.session, run_id)

    state = await load_latest_checkpoint(deps.session, run_id)
    if state is None:
        raise InvalidRunState(
            f"run {run_id} has no checkpoint to revise from",
            details={"run_id": str(run_id)},
        )
    resolved_target = resolve_revision_target(state, target_node)

    await approvals_repo.create(
        deps.session,
        run_id=run_id,
        campaign_version_id=version.id,
        decision=ApprovalDecision.REVISE,
        comment=clean_comment,
        target_node=resolved_target,
    )
    continuation = await continue_run(
        run_id,
        ApprovalDecision.REVISE,
        agents=agents,
        deps=deps,
        comment=clean_comment,
        target_node=resolved_target,
        recorded=True,
    )

    latest = await versions.get_latest(deps.session, run.campaign_id)
    if latest is None:
        raise ValidationFailure(
            f"campaign for run {run_id} has no version after the revision",
            details={"run_id": str(run_id)},
        )
    return RevisionOutcome(run_id=continuation.run_id, version=latest.version)


async def _awaiting_run(session: AsyncSession, run_id: UUID) -> tuple[WorkflowRun, CampaignVersion]:
    """Load a run that is allowed to receive a decision and its reviewed version."""
    run = await runs.get(session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")
    if run.status is not RunStatus.AWAITING_APPROVAL:
        raise InvalidRunState(
            f"run {run_id} is not awaiting approval",
            details={"run_id": str(run_id), "status": run.status.value},
        )

    version = await versions.get_latest(session, run.campaign_id)
    if version is None:
        raise ValidationFailure(
            f"run {run_id} has no campaign version to decide on",
            details={"run_id": str(run_id)},
        )
    return run, version


def _clean_comment(comment: str | None) -> str | None:
    return (comment or "").strip() or None


def _require_comment(comment: str | None) -> str:
    clean = _clean_comment(comment)
    if clean is None:
        raise ValidationFailure("revise requires a non-empty comment")
    return clean
