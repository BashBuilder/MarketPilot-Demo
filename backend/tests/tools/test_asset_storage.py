"""Asset storage: local publishing, remote localisation and provider selection."""

from pathlib import Path

import pytest

from app.agents.designer_targets import to_asset
from app.core.config import Settings
from app.core.errors import ToolError
from app.tools.asset_storage import (
    LocalAssetStorage,
    StoredImageGenerator,
    build_asset_storage,
)
from app.tools.cloudinary_storage import CloudinaryAssetStorage
from app.tools.image_models import GeneratedImage
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


class _RemoteStorage:
    """Stand-in cloud store: records localisation, returns HTTPS URIs."""

    def __init__(self, source: Path) -> None:
        self._source = source
        self.localized: list[str] = []

    async def publish(self, image: GeneratedImage) -> str:
        return f"https://cdn.example.com/{Path(image.path).name}"

    async def localize(self, uri: str) -> Path:
        self.localized.append(uri)
        return self._source


async def test_local_publish_returns_a_relative_uri(tmp_path: Path) -> None:
    generator = StoredImageGenerator(FakeImageGenerator(tmp_path), LocalAssetStorage(tmp_path))

    image = await generator.generate("a calm product shot", "", 3, (8, 8))

    assert image.uri == Path(image.path).name
    assert await LocalAssetStorage(tmp_path).localize(image.uri or "") == image.path


async def test_local_storage_refuses_paths_outside_the_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-{tmp_path.name}.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\n")
    storage = LocalAssetStorage(tmp_path)

    with pytest.raises(ToolError, match="inside the asset directory"):
        await storage.localize(str(outside))
    with pytest.raises(ToolError, match="cannot resolve a remote URI"):
        await storage.localize("https://cdn.example.com/hero.png")


async def test_remote_storage_publishes_and_localizes_before_editing(tmp_path: Path) -> None:
    inner = FakeImageGenerator(tmp_path)
    source = await inner.generate("a calm product shot", "", 3, (8, 8))
    storage = _RemoteStorage(source.path)
    generator = StoredImageGenerator(inner, storage)

    generated = await generator.generate("a calm product shot", "", 9, (8, 8))
    revised = await generator.edit("https://cdn.example.com/hero.png", "make the light warmer")

    assert generated.uri is not None and generated.uri.startswith("https://cdn.example.com/")
    assert storage.localized == ["https://cdn.example.com/hero.png"]
    assert revised.uri is not None and revised.uri.startswith("https://cdn.example.com/")
    assert revised.path.is_file()


def test_cloudinary_requires_its_credentials(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="CLOUDINARY_CLOUD_NAME"):
        build_asset_storage(settings_for(tmp_path, asset_storage="cloudinary"))


def test_cloudinary_is_built_from_settings(tmp_path: Path) -> None:
    storage = build_asset_storage(
        settings_for(
            tmp_path,
            asset_storage="cloudinary",
            cloudinary_cloud_name="demo",
            cloudinary_api_key="key",
            cloudinary_api_secret="secret",
            cloudinary_folder="marketpilot/test",
        )
    )

    assert isinstance(storage, CloudinaryAssetStorage)


def test_local_is_the_default_storage(tmp_path: Path) -> None:
    assert isinstance(build_asset_storage(settings_for(tmp_path)), LocalAssetStorage)


def test_to_asset_prefers_the_published_uri(tmp_path: Path) -> None:
    image = GeneratedImage(
        path=tmp_path / "hero.png",
        checksum="a" * 64,
        model="fake",
        seed=1,
        prompt="Editorial portrait",
        uri="https://cdn.example.com/hero.png",
    )

    assert to_asset(image, tmp_path).uri == "https://cdn.example.com/hero.png"
