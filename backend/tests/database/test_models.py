"""Tests for the ORM models: schema shape, defaults and the append-only guard."""

from collections.abc import Iterator
from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session

from app.database.models import (
    Approval,
    ApprovalDecision,
    Base,
    Campaign,
    CampaignVersion,
    ImmutableVersionError,
    WorkflowRun,
)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _seed(session: Session) -> CampaignVersion:
    campaign = Campaign(idea="Hair care for adults aged 25 to 40")
    session.add(campaign)
    session.flush()

    run = WorkflowRun(campaign_id=campaign.id)
    version = CampaignVersion(
        campaign_id=campaign.id, version=1, package={"brief": {"goal": "awareness"}}
    )
    session.add_all([run, version])
    session.flush()

    session.add(
        Approval(
            run_id=run.id,
            campaign_version_id=version.id,
            decision=ApprovalDecision.APPROVE,
        )
    )
    session.commit()
    return version


def test_registers_expected_tables_and_foreign_key_indexes(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"campaigns", "workflow_runs", "campaign_versions", "approvals"} <= tables

    for table, column in [
        ("workflow_runs", "campaign_id"),
        ("campaign_versions", "campaign_id"),
        ("campaign_versions", "parent_version_id"),
        ("approvals", "run_id"),
        ("approvals", "campaign_version_id"),
    ]:
        names = {index["name"] for index in inspector.get_indexes(table)}
        assert f"ix_{table}_{column}" in names

    version_indexes = {index["name"] for index in inspector.get_indexes("campaign_versions")}
    assert "ix_campaign_versions_campaign_id_version" in version_indexes


def test_rows_get_uuid_keys_and_timestamps(engine: Engine) -> None:
    with Session(engine) as session:
        version = _seed(session)
        campaign = session.get(Campaign, version.campaign_id)
        assert campaign is not None
        assert isinstance(campaign.id, UUID)
        assert isinstance(campaign.created_at, datetime)
        assert isinstance(campaign.updated_at, datetime)
        assert isinstance(version.id, UUID)

        columns = {column["name"] for column in inspect(engine).get_columns("campaign_versions")}
        assert "created_at" in columns
        assert "updated_at" not in columns


def test_version_update_is_rejected(engine: Engine) -> None:
    with Session(engine) as session:
        version = _seed(session)
        version.score = 99.0
        with pytest.raises(ImmutableVersionError):
            session.flush()


def test_version_delete_is_rejected(engine: Engine) -> None:
    with Session(engine) as session:
        version = _seed(session)
        session.delete(version)
        with pytest.raises(ImmutableVersionError):
            session.flush()
