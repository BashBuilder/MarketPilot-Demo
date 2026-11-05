"""Human approval and targeted revision against real PostgreSQL."""

from uuid import UUID

import pytest
from node_fakes import RecordingEmitter
from workflow_loop_fakes import (
    BRIEF,
    RESEARCH,
    REVISED_COPY,
    ScriptedAgent,
    default_agents,
)
from workflow_run_support import (
    add_version,
    checkpoint_nodes,
    dependencies,
    new_run,
    reset_calls,
    run_settings,
)

from app.core.config import Settings
from app.database.models import ApprovalDecision, RunStatus
from app.database.repositories import approvals, runs
from app.graph.workflow import continue_run, run_workflow

pytestmark = pytest.mark.postgres

INITIAL_NODES = [
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "human",
]
REVISION_NODES = [
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "human",
]
WEAKEST_NODES = [
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "human",
]


async def _at_gate(
    factory,
    agents: dict[str, ScriptedAgent],
    emitter: RecordingEmitter,
    settings: Settings,
) -> UUID:
    run_id, campaign_id = await new_run(factory)
    async with factory() as session:
        state = await run_workflow(
            run_id,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )
    assert state.status == "awaiting_approval"
    await add_version(factory, campaign_id)
    return run_id


async def test_revise_with_a_target_reruns_only_from_that_node(pg_session_factory) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id = await _at_gate(pg_session_factory, agents, emitter, settings)

    agents["copywriter"] = ScriptedAgent("copywriter", [REVISED_COPY])
    reset_calls(agents)

    async with pg_session_factory() as session:
        final = await continue_run(
            run_id,
            ApprovalDecision.REVISE,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
            comment="Tighten the claim",
            target_node="copywriter",
        )

    assert final.status == "awaiting_approval"
    assert final.copy == REVISED_COPY
    assert final.brief == BRIEF
    assert final.research == RESEARCH
    assert agents["brief"].calls == 0
    assert agents["research"].calls == 0
    assert agents["copywriter"].calls == 1
    assert agents["creative_director"].calls == 1
    assert agents["designer"].calls == 1
    assert agents["compliance"].calls == 1
    assert agents["reviewer"].calls == 1
    assert await checkpoint_nodes(pg_session_factory, run_id) == [
        *INITIAL_NODES,
        *REVISION_NODES,
    ]


async def test_revise_without_a_target_uses_the_weakest_node(pg_session_factory) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id = await _at_gate(pg_session_factory, agents, emitter, settings)
    reset_calls(agents)

    async with pg_session_factory() as session:
        final = await continue_run(
            run_id,
            ApprovalDecision.REVISE,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
            comment="Improve the audience fit",
        )

    assert final.status == "awaiting_approval"
    assert agents["brief"].calls == 0
    assert agents["research"].calls == 1
    assert agents["copywriter"].calls == 1
    assert agents["reviewer"].calls == 1
    assert await checkpoint_nodes(pg_session_factory, run_id) == [
        *INITIAL_NODES,
        *WEAKEST_NODES,
    ]


async def test_approve_completes_and_emits_the_completed_event(pg_session_factory) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id = await _at_gate(pg_session_factory, agents, emitter, settings)
    reset_calls(agents)

    async with pg_session_factory() as session:
        final = await continue_run(
            run_id,
            ApprovalDecision.APPROVE,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )

    assert final.status == "completed"
    assert all(agent.calls == 0 for agent in agents.values())

    async with pg_session_factory() as session:
        stored = await runs.get(session, run_id)
        approval = await approvals.get_latest_for_run(session, run_id)

    assert stored is not None
    assert stored.status is RunStatus.COMPLETED
    assert stored.current_node is None
    assert approval is not None
    assert approval.decision is ApprovalDecision.APPROVE
    assert (await checkpoint_nodes(pg_session_factory, run_id))[-1] == "end"

    completed = [data for name, data in emitter.events if name == "completed"]
    assert len(completed) == 1
    assert completed[0]["version"] == 1
    assert completed[0]["score"] == 82.0
    assert completed[0]["agent"] == "human"

    reset_calls(agents)
    async with pg_session_factory() as session:
        again = await run_workflow(
            run_id,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )
    assert again.status == "completed"
    assert all(agent.calls == 0 for agent in agents.values())
