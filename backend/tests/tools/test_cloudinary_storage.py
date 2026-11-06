"""Cloudinary storage: signed uploads, error mapping and remote downloads."""

from pathlib import Path

import httpx
import pytest

from app.core.errors import ToolError
from app.tools.cloudinary_client import _sign
from app.tools.cloudinary_storage import CloudinaryAssetStorage
from app.tools.image_models import GeneratedImage
from app.tools.image_png import color_for_seed, png_bytes
from app.tools.image_tools import FakeImageGenerator

_SECRET = "test-secret"


def storage_for(handler: object, tmp_path: Path) -> CloudinaryAssetStorage:
    return CloudinaryAssetStorage(
        cloud_name="demo",
        api_key="test-key",
        api_secret=_SECRET,
        asset_dir=tmp_path,
        folder="marketpilot/test",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


def _field(body: bytes, name: str) -> str:
    marker = f'name="{name}"'.encode()
    start = body.index(marker)
    value_start = body.index(b"\r\n\r\n", start) + 4
    value_end = body.index(b"\r\n", value_start)
    return body[value_start:value_end].decode()


async def test_publish_uploads_signed_bytes_and_returns_the_secure_url(tmp_path: Path) -> None:
    image = await FakeImageGenerator(tmp_path).generate("a calm product shot", "", 5, (8, 8))
    data = image.path.read_bytes()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        captured["url"] = str(request.url)
        captured["body"] = body
        return httpx.Response(
            200,
            json={
                "secure_url": f"https://res.cloudinary.com/demo/image/upload/{image.checksum}.png",
                "bytes": len(data),
            },
        )

    url = await storage_for(handler, tmp_path).publish(image)

    assert url.startswith("https://res.cloudinary.com/demo/image/upload/")
    assert captured["url"] == "https://api.cloudinary.com/v1_1/demo/image/upload"
    body = captured["body"]
    assert isinstance(body, bytes)
    fields = {
        "public_id": _field(body, "public_id"),
        "overwrite": _field(body, "overwrite"),
        "timestamp": _field(body, "timestamp"),
    }
    assert fields["public_id"] == f"marketpilot/test/{image.checksum}"
    assert _field(body, "api_key") == "test-key"
    assert _field(body, "signature") == _sign(fields, _SECRET)


async def test_publish_rejects_a_file_that_does_not_match_the_checksum(tmp_path: Path) -> None:
    data = png_bytes(8, 8, color_for_seed(1))
    path = tmp_path / "tampered.png"
    path.write_bytes(data)
    image = GeneratedImage(
        path=path, checksum="0" * 64, model="fake", seed=1, prompt="a calm product shot"
    )

    with pytest.raises(ToolError, match="checksum mismatch"):
        await storage_for(lambda _: httpx.Response(200), tmp_path).publish(image)


async def test_publish_rejects_a_byte_count_mismatch(tmp_path: Path) -> None:
    image = await FakeImageGenerator(tmp_path).generate("a calm product shot", "", 5, (8, 8))

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"secure_url": "https://cdn.example/hero.png", "bytes": 1})

    with pytest.raises(ToolError, match="different number of bytes"):
        await storage_for(handler, tmp_path).publish(image)


async def test_publish_maps_server_errors_to_retryable_tool_errors(tmp_path: Path) -> None:
    image = await FakeImageGenerator(tmp_path).generate("a calm product shot", "", 5, (8, 8))

    with pytest.raises(ToolError) as excinfo:
        await storage_for(lambda _: httpx.Response(503), tmp_path).publish(image)

    assert excinfo.value.retryable is True
    assert "503" in excinfo.value.message


async def test_localize_downloads_and_validates_a_remote_asset(tmp_path: Path) -> None:
    data = png_bytes(8, 8, color_for_seed(2))
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=data)

    local = await storage_for(handler, tmp_path).localize("https://res.cloudinary.com/demo/x.png")

    assert seen == ["https://res.cloudinary.com/demo/x.png"]
    assert local.is_file()
    assert local.read_bytes() == data


async def test_localize_rejects_a_non_image_payload(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not an image</html>")

    with pytest.raises(ToolError, match="not PNG, JPEG or WebP"):
        await storage_for(handler, tmp_path).localize("https://res.cloudinary.com/demo/x.png")
