"""Run one target across the fixed prompts and collect per-image measurements."""

import importlib
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.tools.image_models import ImageGenerator, Size
from benchmarks.specs import IMAGE_SIZE, PROMPTS, BenchmarkPrompt


@dataclass(slots=True)
class ImageResult:
    """One generation attempt and its measurements."""

    prompt_id: str
    seed: int
    latency_seconds: float
    size_bytes: int | None
    peak_vram_mb: float | None
    path: Path | None
    error: str | None = None


@dataclass(slots=True)
class TargetRun:
    """All attempts for one model plus the aggregates used in the report."""

    model_id: str
    provider: str
    results: list[ImageResult]

    @property
    def failures(self) -> int:
        return sum(1 for result in self.results if result.error is not None)

    @property
    def median_latency(self) -> float | None:
        values = [r.latency_seconds for r in self.results if r.error is None]
        return statistics.median(values) if values else None

    @property
    def peak_vram(self) -> float | None:
        values = [r.peak_vram_mb for r in self.results if r.peak_vram_mb is not None]
        return max(values) if values else None


def _cuda() -> Any:
    """Return torch only when a local CUDA device is visible."""
    try:
        torch: Any = importlib.import_module("torch")
    except ImportError:
        return None
    try:
        return torch if torch.cuda.is_available() else None
    except (AttributeError, RuntimeError):
        return None


def _reset_peak() -> None:
    torch = _cuda()
    if torch is not None:
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()


def _peak_vram_mb() -> float | None:
    torch = _cuda()
    if torch is None:
        return None
    return float(torch.cuda.max_memory_allocated()) / (1024 * 1024)


async def run_target(
    *,
    model_id: str,
    provider: str,
    generator: ImageGenerator,
    output_dir: Path,
    prompts: tuple[BenchmarkPrompt, ...] = PROMPTS,
    size: Size = IMAGE_SIZE,
) -> TargetRun:
    """Generate every prompt sequentially, recording failures instead of stopping."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ImageResult] = []
    for item in prompts:
        _reset_peak()
        started = time.perf_counter()
        try:
            generated = await generator.generate(item.prompt, "", item.seed, size)
        except Exception as exc:  # A benchmark must report a failure and keep going.
            results.append(
                ImageResult(
                    prompt_id=item.prompt_id,
                    seed=item.seed,
                    latency_seconds=time.perf_counter() - started,
                    size_bytes=None,
                    peak_vram_mb=_peak_vram_mb(),
                    path=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        results.append(
            ImageResult(
                prompt_id=item.prompt_id,
                seed=item.seed,
                latency_seconds=time.perf_counter() - started,
                size_bytes=generated.path.stat().st_size,
                peak_vram_mb=_peak_vram_mb(),
                path=generated.path,
            )
        )
    return TargetRun(model_id=model_id, provider=provider, results=results)
