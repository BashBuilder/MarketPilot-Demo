"""Hosted image adapter: HTTP mapping with a mocked transport."""

import base64
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from app.core.errors import ToolError
from app.tools.image_png import png_bytes
from app.tools.image_providers.hosted import HostedImageGenerator

_PNG = png_bytes(8, 8, (12, 34, 56))


def generator(tmp_path: Path, handler: httpx.MockTransport) -> HostedImageGenerator:
    return HostedImageGenerator(
        api_url="https://images.example/v1/generate",
        api_key="test-key",
        asset_dir=tmp_path,
        transport=handler,
    )


async def test_success_writes_a_validated_file_and_sends_the_contract(
    tmp_path: Path,
) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"image_base64": base64.b64encode(_PNG).decode()},
            request=request,
        )

    result = await generator(tmp_path, httpx.MockTransport(handler)).generate(
        "a calm product shot", "blurry", 42, (8, 8)
    )

    assert seen["authorization"] == "Bearer test-key"
    assert seen["body"] == {
        "prompt": "a calm product shot",
        "negative_prompt": "blurry",
        "seed": 42,
        "width": 8,
        "height": 8,
    }
    assert result.path.parent == tmp_path
    assert result.path.suffix == ".png"
    assert result.path.read_bytes() == _PNG
    assert result.checksum == hashlib.sha256(_PNG).hexdigest()
    assert result.model == "hosted"
    assert result.seed == 42


@pytest.mark.parametrize("status", [500, 503])
async def test_5xx_is_retryable(tmp_path: Path, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "unavailable"}, request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "a calm product shot", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is True
    assert excinfo.value.details["status"] == status
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("status", [400, 401, 404, 422])
async def test_4xx_is_not_retryable(tmp_path: Path, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "bad request"}, request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "a calm product shot", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is False
    assert excinfo.value.details["status"] == status


async def test_timeout_is_retryable(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "a calm product shot", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is True
    assert "timed out" in excinfo.value.message


async def test_malformed_image_payload_is_not_retryable(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"image_base64": "not base64"}, request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "a calm product shot", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is False
    assert "base64" in excinfo.value.message


async def test_edit_rejects_a_source_outside_the_asset_directory(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, request=request)

    outside = tmp_path.parent / f"outside-{tmp_path.name}.png"
    outside.write_bytes(_PNG)

    with pytest.raises(ToolError, match="inside the asset directory"):
        await generator(tmp_path, httpx.MockTransport(handler)).edit(outside, "warm lighting")

    assert calls == 0
