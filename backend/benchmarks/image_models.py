"""Benchmark remote Hugging Face image models on five fixed prompts.

Usage:
    uv run python -m benchmarks.image_models --dry-run
    uv run python -m benchmarks.image_models --model stabilityai/sdxl-turbo

No model weights are downloaded. Real runs call Hugging Face Inference
Providers (`hf-inference`) and require ``HUGGINGFACEHUB_API_TOKEN``.
"""

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.core.config import get_settings
from app.tools.image_models import ImageGenerator
from app.tools.image_tools import FakeImageGenerator
from benchmarks.hf_inference import PROVIDER_NAME, HuggingFaceInferenceGenerator
from benchmarks.measure import TargetRun, run_target
from benchmarks.report import render_markdown
from benchmarks.specs import DEFAULT_TARGETS, HFTarget, safe_model_dir, targets_for

DEFAULT_OUTPUT = Path(__file__).with_name("results.md")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="use FakeImageGenerator")
    parser.add_argument(
        "--model",
        action="append",
        default=None,
        metavar="MODEL_ID",
        help="Hugging Face model id to benchmark; repeatable (defaults: three SD models)",
    )
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=None,
        help="defaults to $ASSET_DIR or ./assets",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Markdown report path")
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="per-request timeout in seconds"
    )
    parser.add_argument("--yes", action="store_true", help="skip the pre-run confirmation")
    return parser.parse_args(argv)


def _confirm(targets: Sequence[HFTarget], *, assume_yes: bool) -> bool:
    print("This benchmark calls Hugging Face Inference Providers over HTTP.")
    print("No model weights are downloaded locally; remote usage may consume HF credits.")
    for target in targets:
        print(f"  - {target.model_id} ({target.approx_size})")
    if assume_yes:
        return True
    return input("Type 'yes' to start: ").strip().lower() == "yes"


async def _run(
    targets: Sequence[HFTarget],
    *,
    dry_run: bool,
    token: str | None,
    asset_dir: Path,
    timeout: float,
) -> list[TargetRun]:
    runs: list[TargetRun] = []
    for target in targets:
        model_dir = asset_dir / "benchmarks" / safe_model_dir(target.model_id)
        if dry_run:
            generator: ImageGenerator = FakeImageGenerator(model_dir)
            provider = "fake"
        else:
            generator = HuggingFaceInferenceGenerator(
                model_id=target.model_id,
                api_key=token or "",
                asset_dir=model_dir,
                timeout=timeout,
            )
            provider = PROVIDER_NAME
        runs.append(
            await run_target(
                model_id=target.model_id,
                provider=provider,
                generator=generator,
                output_dir=model_dir,
            )
        )
    return runs


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    asset_dir = args.asset_dir or Path(os.environ.get("ASSET_DIR", "assets"))

    if args.dry_run:
        targets = (HFTarget("fake", "no download"),)
        token = None
    else:
        try:
            settings = get_settings()
        except ValidationError as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 2
        token = (
            settings.huggingfacehub_api_token.get_secret_value()
            if settings.huggingfacehub_api_token
            else ""
        )
        if not token:
            print("Set HUGGINGFACEHUB_API_TOKEN to run a live benchmark.", file=sys.stderr)
            return 2
        model_ids = args.model or [target.model_id for target in DEFAULT_TARGETS]
        targets = targets_for(model_ids)
        if not _confirm(targets, assume_yes=args.yes):
            print("Aborted.")
            return 1

    runs = asyncio.run(
        _run(targets, dry_run=args.dry_run, token=token, asset_dir=asset_dir, timeout=args.timeout)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(runs, datetime.now(UTC)), encoding="utf-8")
    for run in runs:
        print(f"{run.model_id}: {run.failures}/{len(run.results)} failures")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
