"""Escalation path for a graph node after the retry budget is exhausted."""

from uuid import UUID

from node_fakes import IDEA, FakeAgent, RecordingEmitter, event_names
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import RetryExhausted
from app.database.repositories import agent_outputs, checkpoints
from app.graph.nodes import NodeDependencies, make_node
from app.graph.state import WorkflowState
from app.harness.checkpoints import load_latest_checkpoint
from app.harness.verification import VerificationEvent


async def test_retry_exhausted_escalates_without_a_handoff(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> None:
    error = RetryExhausted(
        "output failed verification after 2 attempts",
        details={"attempts": 2},
    )
    agent = FakeAgent(
        error=error,
        verification=(VerificationEvent("validation_failed", 2, 2, ("product: required",)),),
    )
    emitter = RecordingEmitter()
    state = WorkflowState(idea=IDEA)

    async with session_factory() as session:
        node = make_node(
            agent,
            NodeDependencies(
                run_id=run_id,
                llm=object(),
                session=session,
                emit=emitter,
            ),
        )
        result = await node(state)
        await session.commit()

    assert result.status == "escalated"
    assert result.errors == [f"brief: {error.message}"]

    async with session_factory() as session:
        rows = await agent_outputs.list_for_run(session, run_id)
        stored = await load_latest_checkpoint(session, run_id)
        checkpoint_rows = await checkpoints.list_for_run(session, run_id)

    assert rows == []
    assert [row.node for row in checkpoint_rows] == ["brief"]
    assert stored is not None
    assert stored.status == "escalated"
    assert stored.errors == [f"brief: {error.message}"]

    assert event_names(emitter) == ["agent_started", "validation_failed", "error"]
    failure = emitter.events[-1][1]
    assert failure["message"] == error.message
    assert failure["recoverable"] is False
    assert failure["agent"] == "brief"
