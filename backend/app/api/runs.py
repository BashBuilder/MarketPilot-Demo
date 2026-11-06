"""Human approval and revision endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.capacity import ensure_run_capacity
from app.api.dependencies import (
    RunLauncher,
    WorkflowContext,
    get_run_launcher,
    get_workflow_context,
)
from app.api.limits import enforce_write_limit
from app.api.schemas import ApproveRequest, ReviseRequest
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ValidationFailure
from app.database.models import WorkflowRun
from app.database.repositories import runs
from app.graph.approvals import ApprovalOutcome, RevisionOutcome, approve_run, revise_run
from app.harness.registry import ALL_AGENTS

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post(
    "/{run_id}/approve",
    response_model=ApprovalOutcome,
    dependencies=[Depends(enforce_write_limit)],
)
async def approve_run_endpoint(
    run_id: UUID,
    context: Annotated[WorkflowContext, Depends(get_workflow_context)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: ApproveRequest | None = None,
) -> ApprovalOutcome:
    """Record approval and finish the run waiting at the human gate."""
    await _require_run(context.deps.session, run_id)
    comment = _optional_comment(
        payload.comment if payload is not None else None,
        settings.max_comment_length,
    )
    return await approve_run(
        run_id,
        comment,
        agents=context.services.agents,
        deps=context.deps,
    )


@router.post(
    "/{run_id}/revise",
    response_model=RevisionOutcome,
    dependencies=[Depends(enforce_write_limit)],
)
async def revise_run_endpoint(
    run_id: UUID,
    payload: ReviseRequest,
    context: Annotated[WorkflowContext, Depends(get_workflow_context)],
    launcher: Annotated[RunLauncher, Depends(get_run_launcher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RevisionOutcome:
    """Record a revision and launch the new run started from the target node."""
    comment = _required_comment(payload.comment, settings.max_comment_length)
    target_node = _revision_target(payload.target_node)
    await _require_run(context.deps.session, run_id)
    await ensure_run_capacity(context.deps.session, settings)
    outcome = await revise_run(
        run_id,
        comment,
        target_node,
        agents=context.services.agents,
        deps=context.deps,
    )
    await launcher.start(outcome.run_id)
    return outcome


def _optional_comment(value: str | None, max_length: int) -> str | None:
    comment = (value or "").strip()
    if len(comment) > max_length:
        raise ValidationFailure(
            f"comment must be at most {max_length} characters",
            details={"max_length": max_length, "length": len(comment)},
        )
    return comment or None


def _required_comment(value: str, max_length: int) -> str:
    comment = _optional_comment(value, max_length)
    if comment is None:
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
