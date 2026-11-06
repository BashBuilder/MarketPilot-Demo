"""Cloudflare Workers AI adapter: HTTP mapping with a mocked transport."""

import base64
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from app.core.errors import ToolError
from app.tools.image_models import seed_from_digest
from app.tools.image_png import png_bytes
from app.tools.image_providers.cloudflare import CloudflareImageGenerator

_PNG = png_bytes(8, 8, (12, 34, 56))
_FLUX = "@cf/black-forest-labs/flux-1-schnell"
_SDXL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
_EDIT = "@cf/runwayml/stable-diffusion-v1-5-img2img"


def generator(
    tmp_path: Path,
    handler: httpx.MockTransport,
    *,
    model_id: str = _FLUX,
    timeout: float = 45.0,
) -> CloudflareImageGenerator:
    return CloudflareImageGenerator(
        account_id="account",
        api_key="test-key",
        model_id=model_id,
        edit_model_id=_EDIT,
        asset_dir=tmp_path,
        timeout=timeout,
        transport=handler,
    )


async def test_flux_success_decodes_the_json_envelope(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        image = base64.b64encode(_PNG).decode("ascii")
        return httpx.Response(
            200, json={"success": True, "result": {"image": image}}, request=request
        )

    result = await generator(tmp_path, httpx.MockTransport(handler)).generate(
        "a calm product shot", "blurry", 42, (8, 8)
    )

    assert seen["authorization"] == "Bearer test-key"
    assert str(seen["url"]).endswith(f"/accounts/account/ai/run/{_FLUX}")
    assert seen["body"] == {"prompt": "a calm product shot", "steps": 4}
    assert result.path.read_bytes() == _PNG
    assert result.checksum == hashlib.sha256(_PNG).hexdigest()
    assert result.model == f"cloudflare:{_FLUX}"
    assert result.seed == 42


async def test_other_models_send_size_seed_and_negative_prompt(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=_PNG, request=request)

    await generator(tmp_path, httpx.MockTransport(handler), model_id=_SDXL).generate(
        "a calm product shot", "blurry", 7, (16, 16)
    )

    assert seen["body"] == {
        "prompt": "a calm product shot",
        "width": 16,
        "height": 16,
        "seed": 7,
        "negative_prompt": "blurry",
    }


async def test_edit_posts_the_source_and_records_a_derived_seed(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(_PNG)
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=_PNG, request=request)

    result = await generator(tmp_path, httpx.MockTransport(handler)).edit(
        source, "make the lighting warmer"
    )

    body = seen["body"]
    assert str(seen["url"]).endswith(f"/ai/run/{_EDIT}")
    assert isinstance(body, dict)
    assert body["prompt"] == "make the lighting warmer"
    assert base64.b64decode(body["image_b64"]) == _PNG
    checksum = hashlib.sha256(_PNG).hexdigest()
    digest = hashlib.sha256(f"{checksum}:make the lighting warmer".encode()).digest()
    assert result.seed == seed_from_digest(digest)
    assert result.model == f"cloudflare:{_EDIT}"


async def test_missing_image_in_a_json_envelope_is_not_retryable(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "result": {}}, request=request)

    with pytest.raises(ToolError, match="missing image") as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "prompt here", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is False
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("status", [500, 503, 429])
async def test_transient_status_is_retryable(tmp_path: Path, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "unavailable"}, request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "prompt here", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is True
    assert excinfo.value.details["status"] == status


@pytest.mark.parametrize("status", [400, 401, 404])
async def test_client_status_is_not_retryable(tmp_path: Path, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "bad request"}, request=request)

    with pytest.raises(ToolError) as excinfo:
        await generator(tmp_path, httpx.MockTransport(handler)).generate(
            "prompt here", "", 1, (8, 8)
        )

    assert excinfo.value.retryable is False
    assert excinfo.value.details["status"] == status
