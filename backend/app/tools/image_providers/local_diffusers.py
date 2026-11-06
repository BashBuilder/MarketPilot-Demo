"""Local text-to-image backend built on the optional diffusers stack.

Neither ``diffusers`` nor ``torch`` is imported at module import time, so the
project runs without the ``images`` extra. The pipeline loads on first use and
is reused for the life of the process.
"""

import asyncio
import io
import threading
from importlib import import_module
from pathlib import Path
from typing import Any

from app.core.errors import ToolError
from app.tools.image_models import GeneratedImage, Size
from app.tools.image_providers.storage import write_image


class LocalDiffusersGenerator:
    """Runs text-to-image inference on this machine; no hosted API calls."""

    def __init__(self, *, asset_dir: Path, model_id: str, device: str = "cpu") -> None:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        self._asset_dir = asset_dir
        self._model_id = model_id
        self._model = f"local:{model_id}"
        self._device = device
        self._pipeline: Any = None
        self._lock = threading.Lock()

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        size: Size,
    ) -> GeneratedImage:
        data = await asyncio.to_thread(self._render, prompt, negative_prompt, seed, size)
        width, height = size
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"local:{self._model_id}:{prompt}:{negative_prompt}:{seed}:{width}x{height}",
            model=self._model,
            seed=seed,
            prompt=prompt,
        )

    async def edit(self, image_path: Path, instruction: str) -> GeneratedImage:
        del image_path, instruction
        raise ToolError(
            "the local diffusers adapter only supports text-to-image generation",
            retryable=False,
            details={"model": self._model_id},
        )

    def _render(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        size: Size,
    ) -> bytes:
        pipeline = self._get_pipeline()
        torch = self._import("torch")
        generator_type: Any = torch.Generator
        width, height = size
        result: Any = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt or None,
            width=width,
            height=height,
            generator=generator_type(device=self._device).manual_seed(seed),
        )
        images: Any = getattr(result, "images", None)
        if not images:
            raise ToolError("diffusers pipeline returned no images", retryable=False)
        buffer = io.BytesIO()
        images[0].save(buffer, format="PNG")
        return buffer.getvalue()

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        with self._lock:
            if self._pipeline is None:
                self._pipeline = self._load_pipeline()
        return self._pipeline

    def _load_pipeline(self) -> Any:
        diffusers = self._import("diffusers")
        factory: Any = diffusers.AutoPipelineForText2Image
        try:
            return factory.from_pretrained(self._model_id).to(self._device)
        except Exception as exc:
            raise ToolError(
                f"could not load image model: {self._model_id}",
                retryable=True,
                details={"model": self._model_id},
            ) from exc

    @staticmethod
    def _import(module: str) -> Any:
        try:
            return import_module(module)
        except ImportError as exc:
            raise ToolError(
                "IMAGE_PROVIDER=local requires diffusers and torch; "
                "install them with 'uv sync --extra images'",
                retryable=False,
            ) from exc
