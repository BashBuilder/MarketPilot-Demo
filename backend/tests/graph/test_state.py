"""Tests for WorkflowState serialization and invariants."""

import json

import pytest
from pydantic import ValidationError

from app.graph.state import WorkflowState


def test_full_state_round_trips_through_json(full_state: WorkflowState) -> None:
    restored = WorkflowState.model_validate_json(full_state.model_dump_json())

    assert restored == full_state
    assert restored.brief is not None
    assert restored.score is not None
    assert restored.status == "awaiting_approval"


def test_default_state_round_trips() -> None:
    state = WorkflowState(idea="Create a campaign")
    restored = WorkflowState.model_validate_json(state.model_dump_json())

    assert restored == state
    assert restored.brief is None
    assert restored.versions == []
    assert json.loads(state.model_dump_json())["status"] == "pending"


def test_invalid_version_number_is_rejected() -> None:
    with pytest.raises(ValidationError, match="versions"):
        WorkflowState(idea="Create a campaign", versions=[0])


def test_duplicate_versions_are_rejected() -> None:
    with pytest.raises(ValidationError, match="versions must be unique"):
        WorkflowState(idea="Create a campaign", versions=[1, 1])


def test_negative_retry_counter_is_rejected() -> None:
    with pytest.raises(ValidationError, match="non-negative"):
        WorkflowState(idea="Create a campaign", retry_counters={"brief": -1})
