"""Crash resume and repeat-run behavior against real PostgreSQL."""

import pytest
from node_fakes import RecordingEmitter
from workflow_loop_fakes import ASSETS, DIRECTION, ScriptedAgent, default_agents
from workflow_run_support import (
    checkpoint_nodes,
    dependencies,
    new_run,
    reset_calls,
    run_settings,
)

from app.database.repositories import versions
from app.graph.versioning import PACKAGE_FIELDS
from app.graph.workflow import run_workflow
from app.harness.checkpoints import resume_point

pytestmark = pytest.mark.postgres

FIRST_THREE = ["brief", "research", "copywriter"]
FULL_PIPELINE = [
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "human",
]


async def test_crash_after_copywriter_resumes_at_creative_director(
    pg_session_factory,
) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    agents["creative_director"] = ScriptedAgent(
        "creative_director", error=RuntimeError("simulated crash")
    )
    run_id, _ = await new_run(pg_session_factory)

    async with pg_session_factory() as session:
        with pytest.raises(RuntimeError, match="simulated crash"):
            await run_workflow(
                run_id,
                agents=agents,
                deps=dependencies(run_id, session, emitter, settings),
            )

    assert await checkpoint_nodes(pg_session_factory, run_id) == FIRST_THREE
    async with pg_session_factory() as session:
        assert await resume_point(session, run_id) == "creative_director"

    # A fresh session and agent script model the process restarting.
    agents["creative_director"] = ScriptedAgent("creative_director", [DIRECTION])
    async with pg_session_factory() as session:
        final = await run_workflow(
            run_id,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )

    assert final.status == "awaiting_approval"
    assert final.assets == ASSETS
    assert agents["brief"].calls == 1
    assert agents["research"].calls == 1
    assert agents["copywriter"].calls == 1
    assert agents["creative_director"].calls == 1
    assert agents["designer"].calls == 1
    assert agents["compliance"].calls == 1
    assert agents["reviewer"].calls == 1
    assert await checkpoint_nodes(pg_session_factory, run_id) == FULL_PIPELINE


async def test_run_at_the_human_gate_does_not_rerun_any_node(
    pg_session_factory,
) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    run_id, campaign_id = await new_run(pg_session_factory)

    async with pg_session_factory() as session:
        first = await run_workflow(
            run_id,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )
    assert first.status == "awaiting_approval"
    before = await checkpoint_nodes(pg_session_factory, run_id)

    async with pg_session_factory() as session:
        version = await versions.get_latest(session, campaign_id)
        stored_versions = await versions.list_for_campaign(session, campaign_id)
    assert version is not None
    assert version.version == 1
    assert version.parent_version_id is None
    assert set(version.package) == set(PACKAGE_FIELDS)
    assert len(stored_versions) == 1

    reset_calls(agents)

    async with pg_session_factory() as session:
        again = await run_workflow(
            run_id,
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )

    assert again.status == "awaiting_approval"
    assert all(agent.calls == 0 for agent in agents.values())
    assert await checkpoint_nodes(pg_session_factory, run_id) == before
    async with pg_session_factory() as session:
        assert len(await versions.list_for_campaign(session, campaign_id)) == 1
