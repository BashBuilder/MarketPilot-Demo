"""Tests for the offline evaluation fixtures."""

from app.evaluation.datasets import BAD_CLAIM_CASES, CLEAN_CASES, GOLDEN_IDEAS


def test_evaluation_cases_have_unique_ids_and_non_empty_text() -> None:
    cases = (
        [(case.id, case.idea) for case in GOLDEN_IDEAS]
        + [(case.id, case.text) for case in BAD_CLAIM_CASES]
        + [(case.id, case.text) for case in CLEAN_CASES]
    )

    ids = [case_id for case_id, _ in cases]

    assert len(ids) == len(set(ids))
    assert all(text.strip() for _, text in cases)
