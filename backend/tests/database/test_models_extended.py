"""Tests for the remaining models: schema, immutability and the pgvector column."""

from collections.abc import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine, inspect, select
from sqlalchemy.orm import Session

from app.database.models import (
    AgentOutput,
    Asset,
    AssetKind,
    Base,
    Campaign,
    CampaignVersion,
    ImmutableRowError,
    ToolCall,
    WorkflowRun,
)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _seed(session: Session) -> tuple[WorkflowRun, CampaignVersion]:
    campaign = Campaign(idea="Fictional hair care")
    session.add(campaign)
    session.flush()
    run = WorkflowRun(campaign_id=campaign.id)
    version = CampaignVersion(campaign_id=campaign.id, version=1, package={"brief": {}})
    session.add_all([run, version])
    session.commit()
    return run, version


def test_registers_remaining_tables_and_indexes(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "workflow_checkpoints",
        "agent_outputs",
        "assets",
        "compliance_reports",
        "creative_scores",
        "tool_calls",
        "policy_documents",
    } <= tables

    for table, column in [
        ("workflow_checkpoints", "run_id"),
        ("agent_outputs", "run_id"),
        ("assets", "campaign_version_id"),
        ("compliance_reports", "campaign_version_id"),
        ("creative_scores", "campaign_version_id"),
        ("tool_calls", "run_id"),
    ]:
        names = {index["name"] for index in inspector.get_indexes(table)}
        assert f"ix_{table}_{column}" in names

    checkpoint_indexes = {index["name"] for index in inspector.get_indexes("workflow_checkpoints")}
    assert "ix_workflow_checkpoints_run_id_step" in checkpoint_indexes


def test_append_only_rows_reject_mutations(engine: Engine) -> None:
    with Session(engine) as session:
        run, _ = _seed(session)
        output = AgentOutput(run_id=run.id, agent="brief", output={"goal": "awareness"})
        call = ToolCall(
            run_id=run.id,
            agent="research",
            tool="search_tools",
            args_hash="a" * 64,
            duration_ms=12,
            status="ok",
        )
        session.add_all([output, call])
        session.commit()

        output.output = {"goal": "sales"}
        with pytest.raises(ImmutableRowError):
            session.flush()
        session.rollback()

        session.delete(session.get(ToolCall, call.id))
        with pytest.raises(ImmutableRowError):
            session.flush()


def test_asset_stores_generation_metadata(engine: Engine) -> None:
    with Session(engine) as session:
        _, version = _seed(session)
        session.add(
            Asset(
                campaign_version_id=version.id,
                kind=AssetKind.IMAGE,
                uri="file:///assets/hero.png",
                checksum="c" * 64,
                model="flux-schnell",
                seed=42,
                prompt="soft morning light",
                media_type="image/png",
            )
        )
        session.commit()

        asset = session.scalars(select(Asset)).one()
        assert isinstance(asset.id, UUID)
        stored = (asset.uri, asset.checksum, asset.model, asset.seed, asset.prompt)
        assert stored == (
            "file:///assets/hero.png",
            "c" * 64,
            "flux-schnell",
            42,
            "soft morning light",
        )
