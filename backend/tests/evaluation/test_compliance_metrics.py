"""Tests for compliance recall and false-positive evaluation metrics."""

import pytest

from app.evaluation.datasets import BadClaimCase, CleanCase
from app.evaluation.evaluators import compliance_false_positive_rate, compliance_recall

BAD_CASES = (
    BadClaimCase("bad-1", "Guaranteed results.", "guaranteed results"),
    BadClaimCase("bad-2", "A miracle cure.", "miracle or cure wording"),
)
CLEAN_CASES = (
    CleanCase("clean-1", "A gentle daily cleanser."),
    CleanCase("clean-2", "A refillable water bottle."),
)


def test_empty_recall_is_zero() -> None:
    result = compliance_recall((), {})

    assert result.overall == 0.0
    assert result.per_rule == {}


def test_perfect_recall_catches_every_bad_case() -> None:
    result = compliance_recall(BAD_CASES, {"bad-1": True, "bad-2": True})

    assert result.overall == pytest.approx(1.0)
    assert result.per_rule == {
        "guaranteed results": pytest.approx(1.0),
        "miracle or cure wording": pytest.approx(1.0),
    }


def test_worst_recall_catches_no_bad_cases() -> None:
    result = compliance_recall(BAD_CASES, {"bad-1": False, "bad-2": False})

    assert result.overall == 0.0
    assert result.per_rule == {
        "guaranteed results": 0.0,
        "miracle or cure wording": 0.0,
    }


def test_recall_is_split_by_rule_when_results_differ() -> None:
    result = compliance_recall(BAD_CASES, {"bad-1": True, "bad-2": False})

    assert result.overall == pytest.approx(0.5)
    assert result.per_rule["guaranteed results"] == pytest.approx(1.0)
    assert result.per_rule["miracle or cure wording"] == 0.0


def test_missing_verdict_counts_as_not_caught() -> None:
    result = compliance_recall(BAD_CASES, {"bad-1": True})

    assert result.overall == pytest.approx(0.5)
    assert result.per_rule["miracle or cure wording"] == 0.0


def test_empty_false_positive_rate_is_zero() -> None:
    assert compliance_false_positive_rate((), {}) == 0.0


def test_clean_cases_with_no_flags_have_zero_false_positives() -> None:
    result = compliance_false_positive_rate(CLEAN_CASES, {"clean-1": False, "clean-2": False})

    assert result == 0.0


def test_every_clean_case_flagged_is_the_worst_false_positive_rate() -> None:
    result = compliance_false_positive_rate(CLEAN_CASES, {"clean-1": True, "clean-2": True})

    assert result == pytest.approx(1.0)
