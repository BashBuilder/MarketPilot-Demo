"""Checkpoint persistence for graph state and crash recovery.

A checkpoint is an append-only snapshot written after every node. Loading
re-validates the stored JSON through ``WorkflowState`` because the database is
not a trusted boundary: a corrupt or partially migrated row must fail as a
``ValidationFailure`` the harness can escalate, never as a half-built state.
"""

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailure
from app.database.models import WorkflowCheckpoint
from app.database.repositories import checkpoints
from app.graph.state import WorkflowState

_MAX_NODE_NAME = 64


async def save_checkpoint(
    session: AsyncSession,
    run_id: UUID,
    node_name: str,
    state: WorkflowState,
) -> WorkflowCheckpoint:
    """Append a validated snapshot; callers own the transaction that commits it."""
    return await checkpoints.create(
        session,
        run_id=run_id,
        node=_node_name(node_name),
        state=state.model_dump(mode="json"),
    )


async def load_latest_checkpoint(session: AsyncSession, run_id: UUID) -> WorkflowState | None:
    """Return the newest snapshot for a run, or ``None`` if it never checkpointed."""
    try:
        checkpoint = await checkpoints.get_latest(session, run_id)
    except ValueError as exc:
        # SQLAlchemy's JSON decoder raises before we can inspect the row.
        raise ValidationFailure(
            f"latest checkpoint for run {run_id} is not valid JSON",
            details={"run_id": str(run_id)},
        ) from exc

    if checkpoint is None:
        return None

    try:
        return WorkflowState.model_validate(checkpoint.state)
    except ValidationError as exc:
        raise ValidationFailure(
            f"latest checkpoint for run {run_id} failed state validation",
            details={
                "run_id": str(run_id),
                "checkpoint_id": str(checkpoint.id),
                "step": checkpoint.step,
            },
        ) from exc


def _node_name(node_name: str) -> str:
    name = node_name.strip()
    if not name:
        raise ValueError("node_name must not be blank")
    if len(name) > _MAX_NODE_NAME:
        raise ValueError(f"node_name must be at most {_MAX_NODE_NAME} characters")
    return name
