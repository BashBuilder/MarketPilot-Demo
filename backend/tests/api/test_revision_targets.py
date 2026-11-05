"""Validation of the eight accepted revision target names."""

import pytest

from app.api.runs import _revision_target
from app.harness.registry import ALL_AGENTS


@pytest.mark.parametrize("name", sorted(ALL_AGENTS))
def test_revision_target_accepts_every_agent_name(name: str) -> None:
    expected = None if name == "supervisor" else name
    assert _revision_target(name) == expected
