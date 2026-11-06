"""Hugging Face hosted adapter: HTTP mapping with a mocked transport."""

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from app.core.errors import ToolError
from app.tools.image_png import png_bytes
from app.tools.image_providers.huggingface import HuggingFaceImageGenerator

_PNG = png_bytes(8, 8, (12, 34, 56))


def generator(
    tmp_path: Path,
    handler: httpx.MockTransport,
    *,
    timeout: float = 45.0,
) -> HuggingFaceImageGenerator:
    return HuggingFaceImageGenerator(
        model_id="stabilityai/sdxl-turbo",
        api_key="test-key",
        asset_dir=tmp_path,
        timeout=timeout,
        transport=handler,
    )


async def test_success_writes_a_validated_file_and_sends_the_contract(
    tmp_path: Path,
) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=_PNG, request=request)

    result = await generator(tmp_path, httpx.MockTransport(handler)).generate(
        "a calm product shot", "blurry", 42, (8, 8)
    )

    assert seen["authorization"] == "Bearer test-key"
    assert seen["url"].endswith("/hf-inference/models/stabilityai/sdxl-turbo")
    assert seen["body"] == {
        "inputs": "a calm product shot",
        "parameters": {"width": 8, "height": 8, "seed": 42, "negative_prompt": "blurry"},
    }
    assert result.path.parent == tmp_path
    assert result.path.read_bytes() == _PNG
    assert result.checksum == hashlib.sha256(_PNG).hexdigest()
    assert result.model == "hf:stabilityai/sdxl-turbo"
    assert result.seed == 42


async def test_empty_negative_prompt_is_omitted(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=_PNG, request=request)

    await generator(tmp_path, httpx.MockTransport(handler)).generate(
        "a calm product shot", "", 1, (8, 8)
    )

    body = seen["body"]
    assert isinstance(body, dict)
    assert "negative_prompt" not in body["parameters"]


@pytest.mark.parametrize("status", [500, 503, 429])
async def test_transient_status_is_retryable(tmp_path: Path, status: int) -> None:
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
async def test_client_status_is_not_retryable(tmp_path: Path, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "bad request"}, request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "a calm product shot", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is False
    assert excinfo.value.details["status"] == status


async def test_total_deadline_bounds_a_slow_response(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.2)
        return httpx.Response(200, content=_PNG, request=request)

    with pytest.raises(ToolError, match="timed out after") as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler), timeout=0.001).generate(
            "a calm product shot", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is True
    assert not list(tmp_path.iterdir())


async def test_edit_is_rejected_without_a_network_call(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, request=request)

    with pytest.raises(ToolError, match="text-to-image generation") as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).edit(
            tmp_path / "source.png", "make the lighting warmer"
        )

    assert excinfo.value.retryable is False
    assert calls == 0
