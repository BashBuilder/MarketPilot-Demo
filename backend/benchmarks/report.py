"""Render benchmark results to Markdown with blank manual review columns."""

from collections.abc import Sequence
from datetime import datetime

from benchmarks.measure import TargetRun

_NA = "n/a"


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _seconds(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else _NA


def _mb(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else _NA


def _kb(value: int | None) -> str:
    return f"{value / 1024:.1f}" if value is not None else _NA


def render_markdown(runs: Sequence[TargetRun], generated_at: datetime) -> str:
    """Build the summary and per-image tables; quality and licence stay blank."""
    dry_run = any(run.provider == "fake" for run in runs)
    provider_note = (
        "Dry run: generated with `FakeImageGenerator`; no network calls were made."
        if dry_run
        else "Provider: Hugging Face Inference Providers (`hf-inference`, remote)."
    )
    lines = [
        "# Image model benchmark",
        "",
        f"Generated: {generated_at.isoformat(timespec='seconds')}",
        "",
        f"{provider_note} No model weights are downloaded locally; peak VRAM is only "
        "meaningful when a local CUDA device is visible.",
        "",
        "Prompts: the first five `GOLDEN_IDEAS` with fixed seeds.",
        "",
        "## Summary",
        "",
        "| Model | Median latency (s) | Peak VRAM (MB) | Failure count | Quality (1-5) | Licence |",
        "| --- | ---: | ---: | ---: | :---: | :---: |",
    ]
    for run in runs:
        lines.append(
            f"| {_cell(run.model_id)} | {_seconds(run.median_latency)} | "
            f"{_mb(run.peak_vram)} | {run.failures}/{len(run.results)} |  |  |"
        )

    lines.extend(
        [
            "",
            "Quality and licence cells are intentionally blank for manual review.",
            "",
            "## Per-image results",
            "",
            "| Model | Prompt | Seed | Latency (s) | File size (KB) | Peak VRAM (MB) | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for run in runs:
        for result in run.results:
            status = _cell(result.error) if result.error else "ok"
            lines.append(
                f"| {_cell(run.model_id)} | {_cell(result.prompt_id)} | {result.seed} | "
                f"{_seconds(result.latency_seconds)} | {_kb(result.size_bytes)} | "
                f"{_mb(result.peak_vram_mb)} | {status} |"
            )
    return "\n".join(lines) + "\n"
