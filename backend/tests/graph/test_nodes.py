"""Happy path for a graph node: merge, persistence, and event order."""

from uuid import UUID

from node_fakes import IDEA, VALID_BRIEF, FakeAgent, RecordingEmitter, event_names
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.repositories import agent_outputs, checkpoints
from app.graph.nodes import NodeDependencies, make_node
from app.graph.state import WorkflowState
from app.harness.checkpoints import load_latest_checkpoint
from app.harness.verification import VerificationEvent


async def test_node_merges_output_writes_rows_and_checkpoints(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> None:
    agent = FakeAgent(
        VALID_BRIEF,
        verification=(
            VerificationEvent("validation_failed", 1, 2, ("product: required",)),
            VerificationEvent("retrying", 1, 2, ("product: required",), delay=0.5),
        ),
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

    assert result is state
    assert state.brief == VALID_BRIEF
    assert agent.seen_state is not None
    assert agent.seen_state.idea == IDEA
    assert agent.seen_state.brief is None

    async with session_factory() as session:
        rows = await agent_outputs.list_for_run(session, run_id)
        stored = await load_latest_checkpoint(session, run_id)
        checkpoint_rows = await checkpoints.list_for_run(session, run_id)

    assert len(rows) == 1
    assert rows[0].agent == "brief"
    assert rows[0].output == VALID_BRIEF.model_dump(mode="json")
    assert [row.step for row in checkpoint_rows] == [1]
    assert checkpoint_rows[0].node == "brief"
    assert stored == state

    assert event_names(emitter) == [
        "agent_started",
        "validation_failed",
        "retrying",
        "agent_handoff",
    ]
    handoff = emitter.events[-1][1]
    assert handoff["run_id"] == str(run_id)
    assert handoff["agent"] == "brief"
    assert handoff["from"] == "brief"
    assert handoff["to"] == "research"
    assert "timestamp" in handoff
