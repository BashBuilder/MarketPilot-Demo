"""Copywriter Agent: policy lookup allowed, image tools denied."""

import pytest
from copywriter_support import FakePolicy, make_registry

from app.core.errors import GuardrailViolation
from app.tools.policy_tools import POLICY_TOOL_NAME


def test_policy_lookup_is_allowed_for_copywriter() -> None:
    registry = make_registry(FakePolicy())

    spec = registry.get_tool("copywriter", POLICY_TOOL_NAME)

    assert spec.name == POLICY_TOOL_NAME


def test_image_tools_are_denied_for_copywriter() -> None:
    registry = make_registry(FakePolicy())

    with pytest.raises(GuardrailViolation, match="may not use"):
        registry.get_tool("copywriter", "generate_image")
