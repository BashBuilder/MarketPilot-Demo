"""Image tools: deterministic output, metadata and registry permissions."""

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.errors import GuardrailViolation, ToolError
from app.harness.registry import ToolRegistry
from app.tools.image_models import MAX_SEED, seed_from_digest
from app.tools.image_tools import (
    EditImageArgs,
    FakeImageGenerator,
    GeneratedImage,
    GenerateImageArgs,
    register_image_tools,
)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture()
def generator(tmp_path: Path) -> FakeImageGenerator:
    return FakeImageGenerator(tmp_path)


def registry_with(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    register_image_tools(registry, FakeImageGenerator(tmp_path))
    return registry


async def test_generate_writes_a_valid_png(generator: FakeImageGenerator, tmp_path: Path) -> None:
    result = await generator.generate("a calm product shot", "", 42, (8, 8))

    data = result.path.read_bytes()
    assert result.path.parent == tmp_path
    assert data.startswith(_PNG_SIGNATURE)
    assert result.checksum == hashlib.sha256(data).hexdigest()
    assert result.model == "fake"
    assert result.seed == 42
    assert result.prompt == "a calm product shot"


async def test_same_seed_is_deterministic_and_different_seed_differs(
    generator: FakeImageGenerator,
) -> None:
    first = await generator.generate("prompt one", "", 7, (8, 8))
    same_seed = await generator.generate("a different prompt", "blurry", 7, (8, 8))
    other_seed = await generator.generate("prompt one", "", 8, (8, 8))

    assert first.checksum == same_seed.checksum
    assert first.path != same_seed.path
    assert first.checksum != other_seed.checksum


async def test_edit_writes_a_new_file_and_records_the_instruction(
    generator: FakeImageGenerator,
) -> None:
    source = await generator.generate("source product shot", "", 3, (8, 8))
    source_bytes = source.path.read_bytes()

    edited = await generator.edit(source.path, "make the lighting warmer")

    assert edited.path != source.path
    assert edited.path.is_file()
    assert edited.prompt == "make the lighting warmer"
    assert edited.checksum == hashlib.sha256(edited.path.read_bytes()).hexdigest()
    assert source.path.read_bytes() == source_bytes


async def test_edit_rejects_a_source_outside_the_asset_directory(
    generator: FakeImageGenerator, tmp_path: Path
) -> None:
    outside = tmp_path.parent / f"outside-{tmp_path.name}.png"
    outside.write_bytes(_PNG_SIGNATURE)

    with pytest.raises(ToolError, match="inside the asset directory"):
        await generator.edit(outside, "make the lighting warmer")


async def test_registry_registers_both_tools_for_the_designer(tmp_path: Path) -> None:
    registry = registry_with(tmp_path)

    assert {spec.name for spec in registry.allowed_tools("designer")} == {
        "generate_image",
        "edit_image",
    }
    spec = registry.get_tool("designer", "generate_image")
    result = await spec.run(GenerateImageArgs(prompt="valid prompt", seed=1, size=(8, 8)))
    assert isinstance(result, GeneratedImage)
    assert result.path.is_file()


@pytest.mark.parametrize("tool", ["generate_image", "edit_image"])
@pytest.mark.parametrize("agent", ["copywriter", "research", "supervisor"])
def test_non_designer_agents_are_denied(tmp_path: Path, agent: str, tool: str) -> None:
    registry = registry_with(tmp_path)

    with pytest.raises(GuardrailViolation, match="may not use"):
        registry.get_tool(agent, tool)  # type: ignore[arg-type]


def test_seed_from_digest_stays_within_the_bigint_range() -> None:
    assert seed_from_digest(b"\xff" * 32) == MAX_SEED
    assert seed_from_digest(b"\x00" * 32) == 0


def test_args_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        GenerateImageArgs(prompt="valid prompt", seed=-1)
    with pytest.raises(ValidationError):
        GenerateImageArgs(prompt="ok", seed=1)
    with pytest.raises(ValidationError):
        EditImageArgs(image_path=Path("source.png"), instruction="")
