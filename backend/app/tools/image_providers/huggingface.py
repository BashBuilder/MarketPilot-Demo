"""Remote Hugging Face Inference Providers image backend.

The serverless ``hf-inference`` router accepts ``{"inputs": prompt,
"parameters": {...}}`` and returns raw image bytes, so this adapter differs from
the generic JSON/base64 hosted provider. No model weights are downloaded and no
model runs on this machine.
"""

import asyncio
from pathlib import Path

import httpx

from app.core.errors import ToolError
from app.tools.image_models import GeneratedImage, Size
from app.tools.image_providers.storage import validate_image_bytes, write_image

HF_INFERENCE_URL = "https://router.huggingface.co/hf-inference/models"
PROVIDER_NAME = "hf-inference"


class HuggingFaceImageGenerator:
    """Call a hosted open-weight model; nothing is downloaded or run locally."""

    def __init__(
        self,
        *,
        model_id: str,
        api_key: str,
        asset_dir: Path,
        timeout: float = 45.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not model_id.strip() or not api_key:
            raise ValueError("model_id and api_key must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._model_id = model_id.strip()
        self._api_key = api_key
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
        parameters: dict[str, object] = {"width": width, "height": height, "seed": seed}
        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt
        data = await self._post({"inputs": prompt, "parameters": parameters})
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"{self._model_id}:{prompt}:{negative_prompt}:{seed}:{width}x{height}",
            model=f"hf:{self._model_id}",
            seed=seed,
            prompt=prompt,
        )

    async def edit(self, image_path: Path | str, instruction: str) -> GeneratedImage:
        del image_path, instruction
        raise ToolError(
            "the Hugging Face image provider only supports text-to-image generation",
            retryable=False,
            details={"model": self._model_id},
        )

    async def _post(self, payload: dict[str, object]) -> bytes:
        url = f"{HF_INFERENCE_URL}/{self._model_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            data = await asyncio.wait_for(
                self._send(url, payload, headers),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise ToolError(
                f"Hugging Face image request timed out after {self._timeout:g}s",
                retryable=True,
                details={"model": self._model_id, "timeout_seconds": self._timeout},
            ) from exc
        return validate_image_bytes(data)

    async def _send(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> bytes:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ToolError("Hugging Face image request timed out", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ToolError(
                f"Hugging Face image service returned HTTP {status}",
                retryable=status >= 500 or status == 429,
                details={"status": status, "model": self._model_id},
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError("Hugging Face image request failed", retryable=True) from exc
        return response.content
