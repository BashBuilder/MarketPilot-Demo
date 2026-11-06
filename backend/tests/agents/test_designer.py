"""Designer Agent: deterministic assets, flagged-only revisions and caps."""

import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from designer_support import (
    DIRECTION,
    IDEA,
    audit_rows,
    make_tools,
    settings,
    state,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.designer import DesignerAgent
from app.agents.designer_targets import seed_for
from app.agents.outputs import ComplianceItem, ComplianceReport, CreativeDirection
from app.agents.prompts.loader import load_prompt
from app.core.errors import GuardrailViolation
from app.graph.state import WorkflowState


async def test_all_direction_prompts_become_verified_assets(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    tmp_path: Path,
) -> None:
    limits = settings(tmp_path, max_generated_images_per_run=2)
    tools = make_tools(session_factory, run_id, tmp_path, tool_settings=limits)
    workflow = state()
    before = workflow.model_dump()

    result = await DesignerAgent().run(workflow, tools=tools, settings=limits)

    assert workflow.model_dump() == before
    prompts = DIRECTION["image_prompts"]
    assert len(result.assets) == len(prompts)
    for asset, prompt in zip(result.assets, prompts, strict=True):
        data = (tmp_path / asset.uri).read_bytes()
        assert data.startswith(b"\x89PNG")
        assert hashlib.sha256(data).hexdigest() == asset.checksum
        assert asset.model == "fake"
        assert asset.prompt == prompt
    rows = await audit_rows(session_factory, run_id)
    assert [row.tool for row in rows] == ["generate_image"] * len(prompts)
    assert all(row.status == "success" for row in rows)


async def test_revision_regenerates_only_flagged_assets(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    tmp_path: Path,
) -> None:
    limits = settings(tmp_path, max_generated_images_per_run=2)
    tools = make_tools(session_factory, run_id, tmp_path, tool_settings=limits)
    agent = DesignerAgent()
    first = await agent.run(state(), tools=tools, settings=limits)
    report = ComplianceReport(
        items=[
            ComplianceItem(
                check=f"asset {first.assets[0].uri}: visible watermark",
                passed=False,
                reason="Remove the watermark from the background",
            ),
            ComplianceItem(
                check="headline makes a guaranteed-result claim",
                passed=False,
                reason="Rewrite the headline",
            ),
        ]
    )

    revised = await agent.run(
        state(assets=first, compliance=report),
        tools=tools,
        settings=limits,
    )

    assert len(revised.assets) == len(first.assets)
    assert revised.assets[1] == first.assets[1]
    assert revised.assets[0] != first.assets[0]
    assert (tmp_path / revised.assets[0].uri).is_file()
    tools_used = [row.tool for row in await audit_rows(session_factory, run_id)]
    assert tools_used.count("generate_image") == len(first.assets)
    assert tools_used.count("edit_image") == 1


async def test_revision_without_failed_items_keeps_assets_untouched(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    tmp_path: Path,
) -> None:
    limits = settings(tmp_path)
    tools = make_tools(session_factory, run_id, tmp_path, tool_settings=limits)
    agent = DesignerAgent()
    first = await agent.run(state(), tools=tools, settings=limits)
    report = ComplianceReport(
        items=[
            ComplianceItem(
                check="brand voice",
                passed=True,
                reason="Consistent with the approved brief",
            )
        ]
    )

    result = await agent.run(
        state(assets=first, compliance=report),
        tools=tools,
        settings=limits,
    )

    assert result == first
    tools_used = [row.tool for row in await audit_rows(session_factory, run_id)]
    assert tools_used.count("generate_image") == len(first.assets)
    assert "edit_image" not in tools_used


async def test_image_cap_violation_is_not_retried(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    tmp_path: Path,
) -> None:
    limits = settings(tmp_path, max_generated_images_per_run=2, max_image_calls_per_run=1)
    tools = make_tools(session_factory, run_id, tmp_path, tool_settings=limits)

    with pytest.raises(GuardrailViolation, match="image cap of 1"):
        await DesignerAgent().run(state(), tools=tools, settings=limits)

    assert len(list(tmp_path.glob("*.png"))) == 1
    rows = await audit_rows(session_factory, run_id)
    assert sorted(row.status for row in rows) == ["denied", "success"]


async def test_generation_is_limited_to_one_image(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    tmp_path: Path,
) -> None:
    limits = settings(tmp_path)
    tools = make_tools(session_factory, run_id, tmp_path, tool_settings=limits)
    prompts = [f"Editorial still life number {number}" for number in range(1, 7)]
    direction = CreativeDirection.model_validate({**DIRECTION, "image_prompts": prompts})
    workflow = WorkflowState(idea=IDEA, direction=direction)

    result = await DesignerAgent().run(workflow, tools=tools, settings=limits)

    assert [asset.prompt for asset in result.assets] == prompts[:1]
    rows = await audit_rows(session_factory, run_id)
    assert [row.tool for row in rows] == ["generate_image"]
    assert all(row.status == "success" for row in rows)


def test_designer_prompt_is_versioned() -> None:
    assert load_prompt("designer").version == "2"


def test_derived_seeds_are_stable_and_fit_the_database() -> None:
    prompts = [f"Editorial still life number {number}" for number in range(50)]
    seeds = [seed_for(prompt, number) for number, prompt in enumerate(prompts)]

    assert seeds == [seed_for(prompt, number) for number, prompt in enumerate(prompts)]
    assert all(0 <= seed <= 2**63 - 1 for seed in seeds)
