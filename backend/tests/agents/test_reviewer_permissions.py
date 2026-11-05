"""Reviewer Agent: policy lookup allowed, export denied."""

from pathlib import Path

import pytest
from reviewer_support import FakePolicy, make_registry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import GuardrailViolation
from app.harness.registry import ToolRegistry
from app.tools.export_tools import EXPORT_TOOL_NAME, register_export_tools
from app.tools.policy_tools import POLICY_TOOL_NAME


def test_policy_lookup_is_allowed_for_reviewer() -> None:
    registry = make_registry(FakePolicy())

    assert registry.get_tool("reviewer", POLICY_TOOL_NAME).name == POLICY_TOOL_NAME


async def test_export_package_is_denied_for_reviewer(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()
    register_export_tools(registry, session_factory=session_factory, asset_dir=tmp_path)

    allowed = {spec.name for spec in registry.allowed_tools("reviewer")}
    assert EXPORT_TOOL_NAME not in allowed
    with pytest.raises(GuardrailViolation, match="may not use"):
        registry.get_tool("reviewer", EXPORT_TOOL_NAME)
