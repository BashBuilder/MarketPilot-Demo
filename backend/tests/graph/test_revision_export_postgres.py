"""End-to-end Step 11 flow: revise, approve, export and diff two versions."""

import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from node_fakes import RecordingEmitter
from workflow_loop_fakes import COPY, REVISED_COPY, ScriptedAgent, default_agents
from workflow_run_support import dependencies, new_run, reset_calls, run_settings

from app.agents.outputs import Asset, AssetSet
from app.core.errors import GuardrailViolation
from app.database.repositories import versions
from app.graph.approvals import approve_run, revise_run
from app.graph.diff import load_diff
from app.graph.workflow import run_workflow
from app.tools.export_tools import export_package
from app.tools.image_png import png_bytes

pytestmark = pytest.mark.postgres

CHANGED_PATHS = {
    "copy.variants.0.headline",
    "copy.variants.0.description",
    "copy.variants.0.cta",
}


def _exportable_assets(asset_dir: Path) -> AssetSet:
    """Write a real asset so export can verify bytes and copy them."""
    data = png_bytes(8, 8, (51, 102, 153))
    (asset_dir / "hero.png").write_bytes(data)
    return AssetSet(
        assets=[
            Asset(
                uri="hero.png",
                checksum=hashlib.sha256(data).hexdigest(),
                model="fake",
                seed=1,
                prompt="Editorial portrait",
            )
        ]
    )


async def _at_gate(
    factory,
    agents: dict[str, ScriptedAgent],
    emitter,
    settings,
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


async def test_revision_exports_only_after_approval_and_diff_is_minimal(
    pg_session_factory,
    tmp_path: Path,
) -> None:
    settings = run_settings()
    emitter = RecordingEmitter()
    agents = default_agents()
    agents["designer"] = ScriptedAgent("designer", [_exportable_assets(tmp_path)])
    run_id, campaign_id = await _at_gate(pg_session_factory, agents, emitter, settings)
    first_copy = COPY.variants[0]
    revised_copy = REVISED_COPY.variants[0]

    reset_calls(agents)
    agents["copywriter"] = ScriptedAgent("copywriter", [REVISED_COPY])
    async with pg_session_factory() as session:
        revision = await revise_run(
            run_id,
            "Tighten the claim",
            "copywriter",
            agents=agents,
            deps=dependencies(run_id, session, emitter, settings),
        )

    assert revision.version == 2
    async with pg_session_factory() as session:
        second = await versions.get(session, campaign_id, 2)
        assert second is not None
        second_id = second.id

    with pytest.raises(GuardrailViolation, match="no approval"):
        await export_package(
            second_id,
            session_factory=pg_session_factory,
            asset_dir=tmp_path,
        )
    assert not (tmp_path / "exports").exists()

    async with pg_session_factory() as session:
        outcome = await approve_run(
            revision.run_id,
            "Approved after the copy fix",
            agents=agents,
            deps=dependencies(revision.run_id, session, emitter, settings),
        )
    assert outcome.version == 2

    exported = await export_package(
        second_id,
        session_factory=pg_session_factory,
        asset_dir=tmp_path,
    )
    assert exported.version == 2
    assert exported.package_path.is_file()

    async with pg_session_factory() as session:
        diff = await load_diff(session, campaign_id, 1, 2)

    assert diff["from"] == 1
    assert diff["to"] == 2
    assert {change["path"] for change in diff["changes"]} == CHANGED_PATHS
    by_path = {change["path"]: change for change in diff["changes"]}
    assert by_path["copy.variants.0.headline"] == {
        "path": "copy.variants.0.headline",
        "before": first_copy.headline,
        "after": revised_copy.headline,
    }
    assert by_path["copy.variants.0.description"]["after"] == revised_copy.description
    assert by_path["copy.variants.0.cta"]["after"] == revised_copy.cta
