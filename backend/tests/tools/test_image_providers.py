"""Provider selection and lazy-import safety for the image backends."""

import importlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import ToolError
from app.tools.image_providers import build_image_generator
from app.tools.image_providers.hosted import HostedImageGenerator
from app.tools.image_providers.local_diffusers import LocalDiffusersGenerator
from app.tools.image_tools import FakeImageGenerator


def settings_for(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "deepseek_api_key": "test-key",
        "database_url": "postgresql+asyncpg://user:pass@localhost/marketpilot",
        "redis_url": "redis://localhost:6379/0",
        "asset_dir": tmp_path,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_the_default_provider_is_the_fake(tmp_path: Path) -> None:
    assert isinstance(build_image_generator(settings_for(tmp_path)), FakeImageGenerator)


def test_hosted_provider_is_built_from_settings(tmp_path: Path) -> None:
    settings = settings_for(
        tmp_path,
        image_provider="hosted",
        image_api_url="https://images.example/v1/generate",
        image_api_key="secret",
    )

    assert isinstance(build_image_generator(settings), HostedImageGenerator)


def test_hosted_provider_requires_a_url_and_key(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, image_provider="hosted")

    with pytest.raises(RuntimeError, match="IMAGE_API_URL and IMAGE_API_KEY"):
        build_image_generator(settings)


def test_local_provider_is_built_from_settings(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, image_provider="local")

    assert isinstance(build_image_generator(settings), LocalDiffusersGenerator)


def test_unknown_provider_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="image_provider"):
        settings_for(tmp_path, image_provider="flux")


async def test_local_module_works_without_diffusers_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("app.tools.image_providers.local_diffusers")
    monkeypatch.setitem(sys.modules, "diffusers", None)
    monkeypatch.setitem(sys.modules, "torch", None)
    generator = module.LocalDiffusersGenerator(
        asset_dir=tmp_path,
        model_id="stabilityai/sdxl-turbo",
    )

    with pytest.raises(ToolError) as excinfo:
        await generator.generate("a calm product shot", "", 1, (8, 8))

    assert excinfo.value.retryable is False
    assert "--extra images" in excinfo.value.message
    assert not list(tmp_path.iterdir())


async def test_local_edit_is_rejected_without_loading_a_model(tmp_path: Path) -> None:
    generator = LocalDiffusersGenerator(asset_dir=tmp_path, model_id="stabilityai/sdxl-turbo")

    with pytest.raises(ToolError) as excinfo:
        await generator.edit(tmp_path / "source.png", "make the lighting warmer")

    assert excinfo.value.retryable is False
