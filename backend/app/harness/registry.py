"""Tool registry enforcing the per-agent allowlist from agent.md section 5.

Permissions live in code, not in prompts: default deny, and every lookup goes
through the registry. A tool the agent may not use is a guardrail violation,
not an empty result, so callers cannot quietly continue after a denial.
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel

from app.core.errors import GuardrailViolation

type AgentName = Literal[
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
    "supervisor",
]

ALL_AGENTS: frozenset[AgentName] = frozenset(
    (
        "brief",
        "research",
        "copywriter",
        "creative_director",
        "designer",
        "compliance",
        "reviewer",
        "supervisor",
    )
)

# Section 5 allowlist. ``read_state`` is open to every agent except the
# Creative Director, which has no tools at all; ``export_package`` is
# additionally gated on human approval by the export tool.
_READ_STATE_AGENTS = ALL_AGENTS - frozenset({"creative_director"})
DEFAULT_ALLOWLIST: Mapping[str, frozenset[AgentName]] = MappingProxyType(
    {
        "search_tools": frozenset({"research"}),
        "policy_lookup": frozenset({"copywriter", "compliance", "reviewer"}),
        "generate_image": frozenset({"designer"}),
        "edit_image": frozenset({"designer"}),
        "generate_video": frozenset({"designer"}),
        "read_state": _READ_STATE_AGENTS,
        "export_package": frozenset({"reviewer"}),
    }
)


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """A callable the harness is allowed to expose to agents.

    Registration and permission are separate: a registered tool is still
    invisible to an agent unless the allowlist names it.
    """

    name: str
    args_model: type[BaseModel]
    run: Callable[..., Awaitable[Any]]
    side_effecting: bool = False


class ToolRegistry:
    """Holds tool specs and resolves them against an agent allowlist."""

    def __init__(
        self,
        allowlist: Mapping[str, frozenset[AgentName]] | None = None,
    ) -> None:
        self._allowlist = allowlist if allowlist is not None else DEFAULT_ALLOWLIST
        self._specs: dict[str, ToolSpec] = {}

    def register_tool(self, spec: ToolSpec) -> None:
        """Register a tool once; a duplicate name is a programmer error."""
        if spec.name in self._specs:
            raise ValueError(f"tool already registered: {spec.name!r}")
        self._specs[spec.name] = spec

    def allowed_tools(self, agent: AgentName) -> list[ToolSpec]:
        """Return registered tools the agent may use, in registration order."""
        return [
            spec
            for name, spec in self._specs.items()
            if agent in self._allowlist.get(name, frozenset())
        ]

    def get_tool(self, agent: AgentName, name: str) -> ToolSpec:
        """Resolve a tool for an agent or raise ``GuardrailViolation``."""
        spec = self._specs.get(name)
        if spec is None:
            raise GuardrailViolation(
                f"unknown tool: {name!r}",
                details={"agent": agent, "tool": name},
            )
        if agent not in self._allowlist.get(name, frozenset()):
            raise GuardrailViolation(
                f"agent {agent!r} may not use tool {name!r}",
                details={"agent": agent, "tool": name},
            )
        return spec
