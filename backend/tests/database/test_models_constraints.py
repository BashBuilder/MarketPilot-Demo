"""Tests for uniqueness constraints and the pgvector column."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.database.models import (
    Base,
    Campaign,
    CampaignVersion,
    CreativeScore,
    PolicyDocument,
    WorkflowCheckpoint,
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


def test_checkpoint_step_is_unique_per_run(engine: Engine) -> None:
    with Session(engine) as session:
        run, _ = _seed(session)
        session.add_all(
            [
                WorkflowCheckpoint(run_id=run.id, step=1, node="brief", state={}),
                WorkflowCheckpoint(run_id=run.id, step=1, node="brief", state={}),
            ]
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_one_creative_score_per_version(engine: Engine) -> None:
    with Session(engine) as session:
        _, version = _seed(session)
        session.add_all(
            [
                CreativeScore(campaign_version_id=version.id, breakdown={}, total=80.0),
                CreativeScore(campaign_version_id=version.id, breakdown={}, total=75.0),
            ]
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_policy_document_uses_pgvector_and_is_mutable(engine: Engine) -> None:
    ddl = str(CreateTable(PolicyDocument.__table__).compile(dialect=postgresql.dialect()))
    assert "VECTOR(1536)" in ddl.upper()

    inspector = inspect(engine)
    mutable_columns = {column["name"] for column in inspector.get_columns("policy_documents")}
    assert "updated_at" in mutable_columns

    for table in ["agent_outputs", "tool_calls", "workflow_checkpoints", "assets"]:
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert "updated_at" not in columns
