"""Prompt loader: version metadata, body extraction and name safety."""

from pathlib import Path

import pytest

from app.agents.prompts.loader import load_prompt


def test_load_prompt_reads_version_and_body(tmp_path: Path) -> None:
    (tmp_path / "brief.md").write_text(
        "version: 3\n\nWrite a concise campaign brief.\n",
        encoding="utf-8",
    )

    prompt = load_prompt("brief", prompts_dir=tmp_path)

    assert prompt.version == "3"
    assert prompt.text == "Write a concise campaign brief."
    assert "version:" not in prompt.text


def test_load_prompt_requires_a_first_line_version(tmp_path: Path) -> None:
    (tmp_path / "brief.md").write_text("Write a brief.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="version:"):
        load_prompt("brief", prompts_dir=tmp_path)


def test_load_prompt_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid agent name"):
        load_prompt("../brief", prompts_dir=tmp_path)


def test_load_prompt_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="prompt file not found"):
        load_prompt("brief", prompts_dir=tmp_path)
