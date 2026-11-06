"""Fixed benchmark targets and prompts; no model weights are downloaded."""

from dataclasses import dataclass
from typing import Final

from app.evaluation.datasets import GOLDEN_IDEAS


@dataclass(frozen=True, slots=True)
class HFTarget:
    """An open-weight model reached through Hugging Face Inference Providers."""

    model_id: str
    approx_size: str


@dataclass(frozen=True, slots=True)
class BenchmarkPrompt:
    prompt_id: str
    prompt: str
    seed: int


DEFAULT_TARGETS: Final[tuple[HFTarget, ...]] = (
    HFTarget("stabilityai/stable-diffusion-3-medium-diffusers", "~4.3 GB weights"),
    HFTarget("stabilityai/stable-diffusion-xl-base-1.0", "~6.9 GB weights"),
    HFTarget("stabilityai/sdxl-turbo", "~6.9 GB weights"),
)

SEEDS: Final[tuple[int, ...]] = (101, 202, 303, 404, 505)
IMAGE_SIZE: Final[tuple[int, int]] = (512, 512)

PROMPTS: Final[tuple[BenchmarkPrompt, ...]] = tuple(
    BenchmarkPrompt(
        prompt_id=idea.id,
        prompt=f"Editorial advertising image concept: {idea.idea}",
        seed=seed,
    )
    for idea, seed in zip(GOLDEN_IDEAS[:5], SEEDS, strict=True)
)


def targets_for(model_ids: list[str]) -> tuple[HFTarget, ...]:
    """Keep configured sizes for known defaults and label custom ids generically."""
    known = {target.model_id: target for target in DEFAULT_TARGETS}
    return tuple(
        known.get(model_id, HFTarget(model_id, "size not configured")) for model_id in model_ids
    )


def safe_model_dir(model_id: str) -> str:
    """Turn a model id into one path-safe directory name."""
    return "".join(char if char.isalnum() or char in "._-" else "-" for char in model_id)
