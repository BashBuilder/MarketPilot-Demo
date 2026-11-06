"""Tests for the offline evaluation gate."""

import pytest

from app.evaluation import runner


def test_gate_passes_on_the_checked_in_fixtures() -> None:
    report = runner.run_evaluation()

    assert report.schema_total == 8
    assert report.recall.overall == pytest.approx(1.0)
    assert report.passed is True


def test_invalid_golden_payload_fails_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(runner.GOLDEN_OUTPUTS, "brief", {})

    report = runner.run_evaluation()

    assert report.schema_passed < report.schema_total
    assert report.passed is False


def test_main_returns_nonzero_on_a_regression(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(runner.GOLDEN_OUTPUTS, "brief", {})

    assert runner.main() == 1
    assert "evaluation FAILED" in capsys.readouterr().out
