"""Tests for score spread and stability evaluation metrics."""

import pytest

from app.evaluation.evaluators import score_spread, stable


def test_empty_scores_have_zero_spread_and_are_stable() -> None:
    assert score_spread([]) == 0.0
    assert stable([], max_spread=0.0) is True


def test_identical_scores_have_zero_spread() -> None:
    scores = [82.5, 82.5, 82.5]

    assert score_spread(scores) == 0.0
    assert stable(scores, max_spread=0.0) is True


def test_worst_case_exceeds_the_allowed_spread() -> None:
    scores = [40.0, 90.0]

    assert score_spread(scores) == pytest.approx(50.0)
    assert stable(scores, max_spread=10.0) is False


def test_spread_equal_to_the_limit_is_stable() -> None:
    scores = [40.0, 50.0]

    assert score_spread(scores) == pytest.approx(10.0)
    assert stable(scores, max_spread=10.0) is True
