"""Image generation tools and the deterministic fake used in tests and dev.

The protocol keeps the Designer agent independent of any real model: swapping
in a local FLUX or SDXL implementation later only requires another
``ImageGenerator``.
"""

import hashlib
from functools import partial
from pathlib import Path

from app.core.errors import ToolError
from app.harness.registry import ToolRegistry, ToolSpec
from app.tools.image_models import (
    EditImageArgs,
    GeneratedImage,
    GenerateImageArgs,
    ImageGenerator,
    Size,
)
from app.tools.image_png import color_for_seed, is_png, png_bytes, png_size


class FakeImageGenerator:
    """Deterministic stand-in that writes small, valid PNG files.

    Pixel content depends only on seed and size, so the same seed always
    produces the same checksum. The file name also hashes the prompt, keeping
    different prompts from overwriting each other.
    """

    def __init__(self, asset_dir: Path) -> None:
        self._asset_dir = asset_dir
        self._model = "fake"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        size: Size,
    ) -> GeneratedImage:
        width, height = size
        data = png_bytes(width, height, color_for_seed(seed))
        key = f"generate:{prompt}:{negative_prompt}:{seed}:{width}x{height}"
        return self._write(data, key=key, seed=seed, prompt=prompt)

    async def edit(self, image_path: Path, instruction: str) -> GeneratedImage:
        source = self._resolve_source(image_path)
        try:
            source_bytes = source.read_bytes()
        except OSError as exc:
            raise ToolError(
                f"could not read image: {image_path}",
                details={"path": str(image_path)},
            ) from exc
        if not is_png(source_bytes):
            raise ToolError(
                f"source is not a PNG image: {image_path}",
                details={"path": str(image_path)},
            )

        source_checksum = hashlib.sha256(source_bytes).hexdigest()
        seed = int.from_bytes(
            hashlib.sha256(f"{source_checksum}:{instruction}".encode()).digest()[:8],
            "big",
        )
        width, height = png_size(source_bytes)
        data = png_bytes(width, height, color_for_seed(seed))
        key = f"edit:{source_checksum}:{instruction}"
        return self._write(data, key=key, seed=seed, prompt=instruction)

    def _resolve_source(self, image_path: Path) -> Path:
        root = self._asset_dir.resolve()
        candidate = image_path if image_path.is_absolute() else root / image_path
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise ToolError(
                f"image path must be inside the asset directory: {image_path}",
                details={"path": str(image_path), "asset_dir": str(root)},
            )
        if not resolved.is_file():
            raise ToolError(
                f"image not found: {image_path}",
                details={"path": str(image_path)},
            )
        return resolved

    def _write(self, data: bytes, *, key: str, seed: int, prompt: str) -> GeneratedImage:
        self._asset_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(key.encode()).hexdigest()
        path = self._asset_dir / f"{self._model}-{digest[:16]}.png"
        try:
            path.write_bytes(data)
        except OSError as exc:
            raise ToolError(
                f"could not write image: {path}",
                details={"path": str(path)},
            ) from exc
        return GeneratedImage(
            path=path,
            checksum=hashlib.sha256(data).hexdigest(),
            model=self._model,
            seed=seed,
            prompt=prompt,
        )


async def generate_image(
    args: GenerateImageArgs,
    *,
    generator: ImageGenerator,
) -> GeneratedImage:
    return await generator.generate(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        size=args.size,
    )


async def edit_image(
    args: EditImageArgs,
    *,
    generator: ImageGenerator,
) -> GeneratedImage:
    return await generator.edit(image_path=args.image_path, instruction=args.instruction)


def register_image_tools(registry: ToolRegistry, generator: ImageGenerator) -> None:
    """Register both image tools; the allowlist still limits them to Designer."""
    registry.register_tool(
        ToolSpec(
            name="generate_image",
            args_model=GenerateImageArgs,
            run=partial(generate_image, generator=generator),
            side_effecting=True,
        )
    )
    registry.register_tool(
        ToolSpec(
            name="edit_image",
            args_model=EditImageArgs,
            run=partial(edit_image, generator=generator),
            side_effecting=True,
        )
    )
