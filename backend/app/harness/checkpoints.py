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
from app.database.models import ApprovalDecision, RunStatus, WorkflowCheckpoint
from app.database.repositories import approvals, checkpoints, runs, versions
from app.graph.state import WorkflowState

_MAX_NODE_NAME = 64
DONE_NODE = "end"
_DEFAULT_REVISION_NODE = "copywriter"
_PIPELINE = (
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
)
_REVISION_NODES = frozenset(_PIPELINE)
_NEXT_NODE: dict[str, str] = {
    node: _PIPELINE[index + 1] for index, node in enumerate(_PIPELINE[:-1])
}
_NEXT_NODE.update({"reviewer": "human", "human": "human", DONE_NODE: DONE_NODE})


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


async def resume_point(session: AsyncSession, run_id: UUID) -> str:
    """Return the node that should run next after the latest checkpoint."""
    latest = await checkpoints.get_latest(session, run_id)
    if latest is None:
        return _PIPELINE[0]
    try:
        return _NEXT_NODE[latest.node]
    except KeyError:
        raise ValueError(f"unknown checkpoint node: {latest.node!r}") from None


async def request_approval(session: AsyncSession, run_id: UUID) -> None:
    """Persist the gate and pause the run until a human decides."""
    run = await runs.get(session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    state = await load_latest_checkpoint(session, run_id)
    if state is None:
        raise ValidationFailure(
            f"run {run_id} cannot await approval before its first checkpoint",
            details={"run_id": str(run_id)},
        )

    await save_checkpoint(session, run_id, "human", state)
    await runs.set_status(
        session,
        run_id,
        RunStatus.AWAITING_APPROVAL,
        current_node="human",
    )


async def submit_decision(
    session: AsyncSession,
    run_id: UUID,
    decision: ApprovalDecision,
    *,
    comment: str | None = None,
    target_node: str | None = None,
) -> str:
    """Record a human decision and return the node to continue from."""
    run = await runs.get(session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    version = await versions.get_latest(session, run.campaign_id)
    if version is None:
        raise ValidationFailure(
            f"run {run_id} has no campaign version to approve",
            details={"run_id": str(run_id)},
        )

    decision = ApprovalDecision(decision)
    clean_comment = (comment or "").strip() or None
    if decision is ApprovalDecision.REVISE:
        if clean_comment is None:
            raise ValueError("revise requires a non-empty comment")
        next_node = _revision_node(target_node)
        status = RunStatus.RUNNING
        current_node: str | None = next_node
    else:
        next_node = DONE_NODE
        status = RunStatus.COMPLETED
        current_node = None
        target_node = None

    await approvals.create(
        session,
        run_id=run_id,
        campaign_version_id=version.id,
        decision=decision,
        comment=clean_comment,
        target_node=target_node,
    )
    await runs.set_status(session, run_id, status, current_node=current_node)
    return next_node


def _revision_node(target_node: str | None) -> str:
    if target_node is None:
        return _DEFAULT_REVISION_NODE
    name = _node_name(target_node)
    if name not in _REVISION_NODES:
        raise ValueError(f"target_node must be one of {sorted(_REVISION_NODES)}")
    return name


def _node_name(node_name: str) -> str:
    name = node_name.strip()
    if not name:
        raise ValueError("node_name must not be blank")
    if len(name) > _MAX_NODE_NAME:
        raise ValueError(f"node_name must be at most {_MAX_NODE_NAME} characters")
    return name
