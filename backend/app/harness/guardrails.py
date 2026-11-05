"""Per-run budget enforcement and safe delimiters for untrusted prompt text.

Caps are policy, so they belong in code next to the registry: a node that runs
out of image calls or money must stop with a guardrail violation rather than
silently degrade or overspend.
"""

import re
from typing import Final, Literal

from app.core.config import Settings
from app.core.errors import GuardrailViolation

type CapGroup = Literal["image", "search"]

_IMAGE_TOOLS: Final[frozenset[str]] = frozenset({"generate_image", "edit_image", "generate_video"})
_SEARCH_TOOLS: Final[frozenset[str]] = frozenset({"search_tools"})

_SAFE_SOURCE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_-]{1,32}$")
_FORGED_CLOSING_TAG: Final[re.Pattern[str]] = re.compile(r"</\s*untrusted", re.IGNORECASE)


def _cap_group(tool: str) -> CapGroup | None:
    if tool in _IMAGE_TOOLS:
        return "image"
    if tool in _SEARCH_TOOLS:
        return "search"
    return None


class RunGuardrails:
    """Mutable budget for one workflow run, shared by every agent in it.

    A run is a single async task, so plain counters are safe without a lock.
    Counters are keyed per tool and per group, letting the image tools share
    one generation budget instead of each getting a fresh allowance.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._calls: dict[str, int] = {}
        self._group_calls: dict[CapGroup, int] = {}
        self._spent = 0.0

    def record_call(self, tool: str) -> None:
        """Count a tool call, raising when its group budget is exhausted."""
        group = _cap_group(tool)
        if group is not None:
            count = self._group_calls.get(group, 0) + 1
            cap = self._cap_for(group)
            if count > cap:
                raise GuardrailViolation(
                    f"tool {tool!r} exceeded the per-run {group} cap of {cap}",
                    details={"tool": tool, "group": group, "count": count, "cap": cap},
                )
            self._group_calls[group] = count
        self._calls[tool] = self._calls.get(tool, 0) + 1

    def check_cost(self, additional: float) -> None:
        """Pre-flight a projected spend without recording it."""
        if additional < 0:
            raise ValueError("additional cost must not be negative")
        projected = self._spent + additional
        if projected > self._settings.cost_cap_per_run:
            raise GuardrailViolation(
                f"projected run cost {projected:.4f} exceeds cap "
                f"{self._settings.cost_cap_per_run:.4f}",
                details={
                    "spent": self._spent,
                    "additional": additional,
                    "cap": self._settings.cost_cap_per_run,
                },
            )

    def record_cost(self, amount: float) -> None:
        """Add actual spend to the run total, refusing to cross the cap."""
        self.check_cost(amount)
        self._spent += amount

    def calls_for(self, tool: str) -> int:
        return self._calls.get(tool, 0)

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining_cost(self) -> float:
        return self._settings.cost_cap_per_run - self._spent

    def _cap_for(self, group: CapGroup) -> int:
        if group == "image":
            return self._settings.max_image_calls_per_run
        return self._settings.max_search_calls_per_run


def delimit_untrusted(text: str, *, source: str) -> str:
    """Fence retrieved or user-supplied text so it cannot pose as instructions.

    The source is restricted to a safe token because it becomes an attribute,
    and any forged closing tag is neutralised so the block cannot be escaped.
    """
    if not _SAFE_SOURCE.fullmatch(source):
        raise ValueError(f"invalid untrusted source: {source!r}")
    fenced = _FORGED_CLOSING_TAG.sub(r"<\\/untrusted", text)
    return f'<untrusted source="{source}">\n{fenced}\n</untrusted>'
