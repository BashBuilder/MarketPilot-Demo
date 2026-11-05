"""Human approval and revision endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    RunLauncher,
    WorkflowContext,
    get_run_launcher,
    get_workflow_context,
)
from app.api.schemas import ApproveRequest, ReviseRequest
from app.core.errors import NotFoundError, ValidationFailure
from app.database.models import WorkflowRun
from app.database.repositories import runs
from app.graph.approvals import ApprovalOutcome, RevisionOutcome, approve_run, revise_run
from app.harness.registry import ALL_AGENTS

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/{run_id}/approve", response_model=ApprovalOutcome)
async def approve_run_endpoint(
    run_id: UUID,
    context: Annotated[WorkflowContext, Depends(get_workflow_context)],
    payload: ApproveRequest | None = None,
) -> ApprovalOutcome:
    """Record approval and finish the run waiting at the human gate."""
    await _require_run(context.deps.session, run_id)
    comment = payload.comment if payload is not None else None
    return await approve_run(
        run_id,
        comment,
        agents=context.services.agents,
        deps=context.deps,
    )


@router.post("/{run_id}/revise", response_model=RevisionOutcome)
async def revise_run_endpoint(
    run_id: UUID,
    payload: ReviseRequest,
    context: Annotated[WorkflowContext, Depends(get_workflow_context)],
    launcher: Annotated[RunLauncher, Depends(get_run_launcher)],
) -> RevisionOutcome:
    """Record a revision and launch the new run started from the target node."""
    comment = _required_comment(payload.comment)
    target_node = _revision_target(payload.target_node)
    await _require_run(context.deps.session, run_id)
    outcome = await revise_run(
        run_id,
        comment,
        target_node,
        agents=context.services.agents,
        deps=context.deps,
    )
    await launcher.start(outcome.run_id)
    return outcome


def _required_comment(value: str) -> str:
    comment = value.strip()
    if not comment:
        raise ValidationFailure("revise requires a non-empty comment")
    return comment


def _revision_target(value: str | None) -> str | None:
    if value is None:
        return None
    target = value.strip()
    if target not in ALL_AGENTS:
        raise ValidationFailure(
            "target_node must be one of the eight agent names",
            details={"target_node": value, "allowed": sorted(ALL_AGENTS)},
        )
    # The Supervisor routes instead of producing a package field, so naming it
    # is equivalent to letting the Supervisor choose the weakest node.
    return None if target == "supervisor" else target


async def _require_run(session: AsyncSession, run_id: UUID) -> WorkflowRun:
    run = await runs.get(session, run_id)
    if run is None:
        raise NotFoundError(f"run not found: {run_id}", details={"id": str(run_id)})
    return run
