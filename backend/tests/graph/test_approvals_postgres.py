"""Human approval and revision operations against real PostgreSQL."""

from uuid import UUID

import pytest
from node_fakes import RecordingEmitter
from workflow_loop_fakes import COPY, REVISED_COPY, ScriptedAgent, default_agents
from workflow_run_support import dependencies, new_run, reset_calls, run_settings

from app.core.config import Settings
from app.core.errors import InvalidRunState, ValidationFailure
from app.database.models import ApprovalDecision, RunStatus
from app.database.repositories import approvals, runs, versions
from app.graph.approvals import approve_run, revise_run
from app.graph.workflow import run_workflow

pytestmark = pytest.mark.postgres


async def _at_gate(
    factory,
    agents: dict[str, ScriptedAgent],
    emitter: RecordingEmitter,
    settings: Settings,
) -> tuple[UUID, UUID]:
    run_id, campaign_id = await new_run(factory)
    async with factory() as session:
        state = await run_workflow(
            run_id,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )
    assert state.status == "awaiting_approval"
    return run_id, campaign_id


async def test_approve_records_a_row_and_completes(pg_session_factory) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id, _ = await _at_gate(pg_session_factory, agents, emitter, settings)
    reset_calls(agents)

    async with pg_session_factory() as session:
        outcome = await approve_run(
            run_id,
            "Looks good",
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )

    assert outcome.model_dump() == {"status": "completed", "version": 1}
    assert all(agent.calls == 0 for agent in agents.values())

    async with pg_session_factory() as session:
        stored = await runs.get(session, run_id)
        rows = await approvals.list_for_run(session, run_id)

    assert stored is not None
    assert stored.status is RunStatus.COMPLETED
    assert len(rows) == 1
    assert rows[0].decision is ApprovalDecision.APPROVE
    assert rows[0].comment == "Looks good"

    completed = [data for name, data in emitter.events if name == "completed"]
    assert completed
    assert completed[-1]["version"] == 1


async def test_revise_creates_version_two_and_feeds_the_target_context(
    pg_session_factory,
) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id, campaign_id = await _at_gate(pg_session_factory, agents, emitter, settings)
    reset_calls(agents)
    agents["copywriter"] = ScriptedAgent("copywriter", [REVISED_COPY])

    async with pg_session_factory() as session:
        outcome = await revise_run(
            run_id,
            "Tighten the claim",
            "copywriter",
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )

    assert outcome.model_dump() == {"run_id": outcome.run_id, "version": 2}
    assert outcome.run_id != run_id

    async with pg_session_factory() as session:
        first = await versions.get(session, campaign_id, 1)
        second = await versions.get(session, campaign_id, 2)
        old_run = await runs.get(session, run_id)
        new_run = await runs.get(session, outcome.run_id)
        rows = await approvals.list_for_run(session, run_id)

    assert first is not None
    assert second is not None
    assert second.parent_version_id == first.id
    assert second.package["copy"] == REVISED_COPY.model_dump(mode="json")
    assert first.package["copy"] == COPY.model_dump(mode="json")

    assert old_run is not None
    assert old_run.status is RunStatus.COMPLETED
    assert new_run is not None
    assert new_run.status is RunStatus.AWAITING_APPROVAL
    assert new_run.campaign_id == campaign_id

    assert len(rows) == 1
    assert rows[0].decision is ApprovalDecision.REVISE
    assert rows[0].comment == "Tighten the claim"
    assert rows[0].target_node == "copywriter"

    revised = agents["copywriter"]
    assert revised.seen_state is not None
    assert revised.seen_state.revision_feedback == "Tighten the claim"
    assert revised.seen_state.copy == COPY
    assert agents["brief"].calls == 0
    assert agents["research"].calls == 0


async def test_revise_without_a_comment_is_rejected(pg_session_factory) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id, campaign_id = await _at_gate(pg_session_factory, agents, emitter, settings)

    async with pg_session_factory() as session:
        with pytest.raises(ValidationFailure, match="comment"):
            await revise_run(
                run_id,
                "   ",
                agents=agents,
                deps=dependencies(run_id, session, emitter, settings),
            )
        rows = await approvals.list_for_run(session, run_id)
        stored_versions = await versions.list_for_campaign(session, campaign_id)

    assert rows == []
    assert len(stored_versions) == 1


async def test_approving_a_run_that_is_not_awaiting_approval_raises(
    pg_session_factory,
) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id, _ = await new_run(pg_session_factory)

    async with pg_session_factory() as session:
        with pytest.raises(InvalidRunState):
            await approve_run(
                run_id,
                None,
                agents=agents,
                deps=dependencies(run_id, session, emitter, settings),
            )
