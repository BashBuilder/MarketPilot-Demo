"""Typed models and the backend protocol for image generation tools."""

from pathlib import Path
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field

MAX_IMAGE_DIMENSION = 2048
DEFAULT_IMAGE_SIZE: tuple[int, int] = (256, 256)
# The seed is persisted in a BIGINT column, so derived seeds must fit int64.
MAX_SEED = 2**63 - 1
_CHECKSUM_PATTERN = r"^[0-9a-f]{64}$"


def seed_from_digest(digest: bytes) -> int:
    """Fold digest bytes into a non-negative seed PostgreSQL can store."""
    return int.from_bytes(digest[:8], "big") & MAX_SEED


type Dimension = Annotated[int, Field(ge=1, le=MAX_IMAGE_DIMENSION)]
type Size = tuple[Dimension, Dimension]


class GeneratedImage(BaseModel):
    """Metadata for one written image file; the bytes stay on disk."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    path: Path
    checksum: Annotated[str, Field(pattern=_CHECKSUM_PATTERN)]
    model: Annotated[str, Field(min_length=2)]
    seed: Annotated[int, Field(ge=0)]
    prompt: Annotated[str, Field(min_length=1)]
    # Public URI assigned by the asset store; the local path stays the working copy.
    uri: str | None = None


class GenerateImageArgs(BaseModel):
    """Validated arguments for ``generate_image``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prompt: Annotated[str, Field(min_length=5, max_length=2000)]
    negative_prompt: Annotated[str, Field(max_length=2000)] = ""
    seed: Annotated[int, Field(ge=0)]
    size: Size = DEFAULT_IMAGE_SIZE


class EditImageArgs(BaseModel):
    """Validated arguments for ``edit_image``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    image_path: str | Path
    instruction: Annotated[str, Field(min_length=5, max_length=2000)]


class ImageGenerator(Protocol):
    """Backend that turns prompts or edit instructions into image files."""

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        size: Size,
    ) -> GeneratedImage: ...

    async def edit(self, image_path: Path | str, instruction: str) -> GeneratedImage: ...
