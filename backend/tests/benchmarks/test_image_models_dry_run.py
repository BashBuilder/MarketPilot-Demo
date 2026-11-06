"""Dry-run benchmark: fake backend only, no network calls."""

from pathlib import Path

from benchmarks.image_models import main

SUMMARY_HEADER = (
    "| Model | Median latency (s) | Peak VRAM (MB) | Failure count | Quality (1-5) | Licence |"
)


def test_dry_run_writes_five_images_and_a_report(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    output = tmp_path / "results.md"

    exit_code = main(["--dry-run", "--asset-dir", str(asset_dir), "--output", str(output)])

    assert exit_code == 0
    images = sorted((asset_dir / "benchmarks" / "fake").glob("*.png"))
    assert len(images) == 5
    report = output.read_text(encoding="utf-8")
    assert SUMMARY_HEADER in report
    assert "Dry run: generated with `FakeImageGenerator`" in report
    assert "## Per-image results" in report
    assert report.count("| ok |") == 5

    summary_row = next(line for line in report.splitlines() if line.startswith("| fake |"))
    cells = [cell.strip() for cell in summary_row.strip("|").split("|")]
    assert cells[1] != ""
    assert cells[3] == "0/5"
    assert cells[4] == ""
    assert cells[5] == ""
