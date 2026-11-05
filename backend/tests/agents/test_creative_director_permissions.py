"""Creative Director Agent: no tools, so every tool call is denied."""

import pytest
from pydantic import BaseModel

from app.core.errors import GuardrailViolation
from app.harness.registry import DEFAULT_ALLOWLIST, ToolRegistry, ToolSpec


class EmptyArgs(BaseModel):
    pass


async def noop() -> None:
    return None


def registry() -> ToolRegistry:
    reg = ToolRegistry()
    for name in DEFAULT_ALLOWLIST:
        reg.register_tool(ToolSpec(name=name, args_model=EmptyArgs, run=noop))
    return reg


def test_creative_director_has_an_empty_allowlist() -> None:
    assert registry().allowed_tools("creative_director") == []


@pytest.mark.parametrize("tool", tuple(DEFAULT_ALLOWLIST))
def test_every_tool_call_is_denied(tool: str) -> None:
    with pytest.raises(GuardrailViolation, match="may not use"):
        registry().get_tool("creative_director", tool)
