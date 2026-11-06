"""Cloudflare Workers AI image backend over the REST Run API.

The Run API accepts model-specific JSON at
``/accounts/{account_id}/ai/run/{model}`` and returns either raw image bytes or
a JSON envelope whose ``result.image`` is base64. Both shapes are handled here
because Workers AI models differ. Nothing is downloaded or run locally.
"""

import asyncio
import base64
import hashlib
from pathlib import Path

import httpx

from app.core.errors import ToolError
from app.tools.image_models import GeneratedImage, Size, seed_from_digest
from app.tools.image_providers.storage import (
    decode_base64,
    read_source,
    validate_image_bytes,
    write_image,
)

API_BASE = "https://api.cloudflare.com/client/v4/accounts"
FLUX_SCHNELL = "@cf/black-forest-labs/flux-1-schnell"


class CloudflareImageGenerator:
    """Call Workers AI models; no model weights touch this machine."""

    def __init__(
        self,
        *,
        account_id: str,
        api_key: str,
        model_id: str,
        edit_model_id: str,
        asset_dir: Path,
        timeout: float = 45.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not account_id.strip() or not api_key:
            raise ValueError("account_id and api_key must not be empty")
        if not model_id.strip() or not edit_model_id.strip():
            raise ValueError("model ids must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._account_id = account_id.strip()
        self._api_key = api_key
        self._model_id = model_id.strip()
        self._edit_model_id = edit_model_id.strip()
        self._asset_dir = asset_dir
        self._timeout = timeout
        self._transport = transport

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        size: Size,
    ) -> GeneratedImage:
        width, height = size
        payload: dict[str, object] = {"prompt": prompt}
        if self._model_id == FLUX_SCHNELL:
            # FLUX.1 schnell rejects size and seed; steps is capped at 8.
            payload["steps"] = 4
        else:
            payload.update(
                {
                    "width": width,
                    "height": height,
                    "seed": seed,
                }
            )
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
        data = await self._post(self._model_id, payload)
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"cloudflare:{self._model_id}:{prompt}:{negative_prompt}:{seed}:{width}x{height}",
            model=f"cloudflare:{self._model_id}",
            seed=seed,
            prompt=prompt,
        )

    async def edit(self, image_path: Path | str, instruction: str) -> GeneratedImage:
        source = validate_image_bytes(read_source(Path(image_path), self._asset_dir))
        payload: dict[str, object] = {
            "prompt": instruction,
            "image_b64": base64.b64encode(source).decode("ascii"),
        }
        data = await self._post(self._edit_model_id, payload)
        checksum = hashlib.sha256(source).hexdigest()
        digest = hashlib.sha256(f"{checksum}:{instruction}".encode()).digest()
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"cloudflare-edit:{self._edit_model_id}:{checksum}:{instruction}",
            model=f"cloudflare:{self._edit_model_id}",
            seed=seed_from_digest(digest),
            prompt=instruction,
        )

    async def _post(self, model_id: str, payload: dict[str, object]) -> bytes:
        url = f"{API_BASE}/{self._account_id}/ai/run/{model_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = await asyncio.wait_for(
                self._send(url, payload, headers),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise ToolError(
                f"Cloudflare image request timed out after {self._timeout:g}s",
                retryable=True,
                details={"model": model_id, "timeout_seconds": self._timeout},
            ) from exc
        return _decode_image(response, model_id)

    async def _send(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ToolError("Cloudflare image request timed out", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ToolError(
                f"Cloudflare image service returned HTTP {status}",
                retryable=status >= 500 or status == 429,
                details={"status": status, "model": url.rsplit("/", 1)[-1]},
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError("Cloudflare image request failed", retryable=True) from exc
        return response


def _decode_image(response: httpx.Response, model_id: str) -> bytes:
    """Decode both Workers AI response shapes without trusting either one."""
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type == "application/json" or content_type.endswith("+json"):
        try:
            body = response.json()
        except ValueError as exc:
            raise ToolError("Cloudflare image service returned invalid JSON") from exc
        image = body.get("image") if isinstance(body, dict) else None
        if image is None and isinstance(body, dict):
            result = body.get("result")
            image = result.get("image") if isinstance(result, dict) else None
        if not isinstance(image, str) or not image:
            raise ToolError(
                "Cloudflare image service response is missing image",
                details={"model": model_id},
            )
        return decode_base64(image)
    return validate_image_bytes(response.content)
