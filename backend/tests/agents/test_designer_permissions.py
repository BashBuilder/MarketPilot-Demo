"""Designer Agent: image tools allowed, every other agent denied."""

from pathlib import Path

import pytest

from app.core.errors import GuardrailViolation
from app.harness.registry import ToolRegistry
from app.tools.image_tools import FakeImageGenerator, register_image_tools

NON_DESIGNERS = (
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "compliance",
    "reviewer",
    "supervisor",
)


def registry(asset_dir: Path) -> ToolRegistry:
    reg = ToolRegistry()
    register_image_tools(reg, FakeImageGenerator(asset_dir))
    return reg


def test_designer_may_generate_and_edit(tmp_path: Path) -> None:
    tools = registry(tmp_path)

    assert {spec.name for spec in tools.allowed_tools("designer")} == {
        "generate_image",
        "edit_image",
    }


@pytest.mark.parametrize("agent", NON_DESIGNERS)
@pytest.mark.parametrize("tool", ("generate_image", "edit_image"))
def test_non_designer_is_denied(tmp_path: Path, agent: str, tool: str) -> None:
    with pytest.raises(GuardrailViolation, match="may not use"):
        registry(tmp_path).get_tool(agent, tool)  # type: ignore[arg-type]
