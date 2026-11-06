"""Hosted HTTP image generator.

Wire contract behind ``IMAGE_API_URL``: ``POST <url>`` with
``{prompt, negative_prompt, seed, width, height}`` for generation and
``POST <url>/edit`` with ``{instruction, image_base64}`` for edits. A 2xx
response is JSON ``{"image_base64": "<png|jpeg|webp bytes>"}``; requests carry
``Authorization: Bearer <IMAGE_API_KEY>``. Only transient failures (timeouts,
transport errors, 5xx) are retryable; a 4xx or malformed payload is not.
"""

import asyncio
import base64
import hashlib
from pathlib import Path

import httpx

from app.core.errors import ToolError
from app.tools.image_models import GeneratedImage, Size
from app.tools.image_providers.storage import decode_base64, read_source, write_image


class HostedImageGenerator:
    """Adapter for a remote text-to-image service; no model runs locally."""

    def __init__(
        self,
        *,
        api_url: str,
        api_key: str,
        asset_dir: Path,
        timeout: float = 120.0,
        model: str = "hosted",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_url.strip() or not api_key:
            raise ValueError("api_url and api_key must not be empty")
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._asset_dir = asset_dir
        self._timeout = timeout
        self._model = model
        self._transport = transport

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        size: Size,
    ) -> GeneratedImage:
        width, height = size
        payload: dict[str, object] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "width": width,
            "height": height,
        }
        data = await self._post(self._api_url, payload)
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"hosted:{prompt}:{negative_prompt}:{seed}:{width}x{height}",
            model=self._model,
            seed=seed,
            prompt=prompt,
        )

    async def edit(self, image_path: Path, instruction: str) -> GeneratedImage:
        source = read_source(image_path, self._asset_dir)
        data = await self._post(
            f"{self._api_url}/edit",
            {"instruction": instruction, "image_base64": base64.b64encode(source).decode()},
        )
        checksum = hashlib.sha256(source).hexdigest()
        digest = hashlib.sha256(f"{checksum}:{instruction}".encode()).digest()
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"hosted-edit:{checksum}:{instruction}",
            model=self._model,
            seed=int.from_bytes(digest[:8], "big"),
            prompt=instruction,
        )

    async def _post(self, url: str, payload: dict[str, object]) -> bytes:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = await asyncio.wait_for(
                self._send(url, payload, headers),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise ToolError(
                f"hosted image request timed out after {self._timeout:g}s",
                retryable=True,
                details={"timeout_seconds": self._timeout},
            ) from exc
        return decode_base64(self._extract(response))

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
            raise ToolError("hosted image request timed out", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ToolError(
                f"hosted image service returned HTTP {status}",
                retryable=status >= 500,
                details={"status": status},
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError("hosted image request failed", retryable=True) from exc
        return response

    @staticmethod
    def _extract(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError as exc:
            raise ToolError("hosted image service returned invalid JSON") from exc
        payload = body.get("image_base64") if isinstance(body, dict) else None
        if not isinstance(payload, str) or not payload:
            raise ToolError("hosted image service response is missing image_base64")
        return payload
