"""Allow, deny and unknown-tool behaviour of the per-agent registry."""

from typing import cast

import pytest
from pydantic import BaseModel

from app.core.errors import GuardrailViolation
from app.harness.registry import (
    ALL_AGENTS,
    DEFAULT_ALLOWLIST,
    AgentName,
    ToolRegistry,
    ToolSpec,
)

TOOL_NAMES = tuple(DEFAULT_ALLOWLIST)


class EmptyArgs(BaseModel):
    pass


async def noop() -> None:
    return None


def spec(name: str) -> ToolSpec:
    return ToolSpec(name=name, args_model=EmptyArgs, run=noop)


def registry() -> ToolRegistry:
    reg = ToolRegistry()
    for name in TOOL_NAMES:
        reg.register_tool(spec(name))
    return reg


def names(specs: list[ToolSpec]) -> set[str]:
    return {item.name for item in specs}


def test_allowed_tools_follow_the_allowlist() -> None:
    reg = registry()

    assert names(reg.allowed_tools("research")) == {"search_tools", "read_state"}
    assert names(reg.allowed_tools("designer")) == {
        "generate_image",
        "edit_image",
        "generate_video",
        "read_state",
    }
    assert names(reg.allowed_tools("copywriter")) == {"policy_lookup", "read_state"}
    assert names(reg.allowed_tools("reviewer")) == {
        "policy_lookup",
        "read_state",
        "export_package",
    }
    assert names(reg.allowed_tools("supervisor")) == {"read_state"}


@pytest.mark.parametrize("agent", sorted(ALL_AGENTS))
def test_every_agent_can_read_state(agent: AgentName) -> None:
    assert registry().get_tool(agent, "read_state").name == "read_state"


def test_denied_tool_raises_guardrail_violation() -> None:
    with pytest.raises(GuardrailViolation, match="may not use"):
        registry().get_tool("copywriter", "generate_image")


def test_unknown_tool_raises_guardrail_violation() -> None:
    with pytest.raises(GuardrailViolation, match="unknown tool"):
        registry().get_tool("research", "delete_database")


def test_registered_but_unlisted_tool_is_denied() -> None:
    reg = registry()
    reg.register_tool(spec("internal_only"))

    assert "internal_only" not in names(reg.allowed_tools("supervisor"))
    with pytest.raises(GuardrailViolation, match="may not use"):
        reg.get_tool("supervisor", "internal_only")


def test_unknown_agent_is_denied_by_default() -> None:
    intruder = cast(AgentName, "intern")

    assert registry().allowed_tools(intruder) == []
    with pytest.raises(GuardrailViolation, match="may not use"):
        registry().get_tool(intruder, "read_state")


def test_duplicate_registration_is_rejected() -> None:
    reg = registry()

    with pytest.raises(ValueError, match="already registered"):
        reg.register_tool(spec("search_tools"))


def test_tool_spec_is_immutable() -> None:
    tool = spec("search_tools")

    with pytest.raises(AttributeError):
        tool.name = "other"  # type: ignore[misc]
