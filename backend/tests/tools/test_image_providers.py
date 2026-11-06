"""Provider selection and validation for the remote image backends."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.tools.image_providers import build_image_generator
from app.tools.image_providers.hosted import HostedImageGenerator
from app.tools.image_providers.huggingface import HuggingFaceImageGenerator
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


def test_huggingface_provider_is_built_from_settings(tmp_path: Path) -> None:
    settings = settings_for(
        tmp_path,
        image_provider="huggingface",
        image_model_id="stabilityai/sdxl-turbo",
        huggingfacehub_api_token="secret",
    )

    generator = build_image_generator(settings)

    assert isinstance(generator, HuggingFaceImageGenerator)
    assert generator._model_id == "stabilityai/sdxl-turbo"


def test_huggingface_provider_requires_a_token(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, image_provider="huggingface")

    with pytest.raises(RuntimeError, match="HUGGINGFACEHUB_API_TOKEN"):
        build_image_generator(settings)


def test_unknown_provider_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="image_provider"):
        settings_for(tmp_path, image_provider="flux")
