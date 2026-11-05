"""Validation tests for CreativeScore and its rubric total."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.creative_score import CreativeScore


def dimension(score: float) -> dict[str, object]:
    return {"score": score, "justification": "Clear rationale for this dimension."}


VALID = {
    "brief_alignment": dimension(8),
    "audience_fit": dimension(7),
    "copy_quality": dimension(9),
    "visual_quality": dimension(8),
    "compliance_risk": dimension(6),
    "total": 76.0,
}
INVALID = {**VALID, "total": 80.0}


def test_valid_score_parses() -> None:
    score = CreativeScore.model_validate(VALID)

    assert score.total == 76.0
    assert score.copy_quality.score == 9


def test_total_mismatch_is_rejected() -> None:
    with pytest.raises(ValidationError, match="total must equal the weighted dimensions"):
        CreativeScore.model_validate(INVALID)


def test_out_of_range_dimension_is_rejected() -> None:
    payload = {**VALID, "brief_alignment": dimension(10.5)}

    with pytest.raises(ValidationError, match="brief_alignment"):
        CreativeScore.model_validate(payload)


def test_multiline_justification_is_rejected() -> None:
    payload = {
        **VALID,
        "copy_quality": {
            "score": 9,
            "justification": "Strong hooks.\nWeak closing line.",
        },
    }

    with pytest.raises(ValidationError, match="single line"):
        CreativeScore.model_validate(payload)


def test_boundary_totals_are_accepted() -> None:
    zero = {name: dimension(0) for name in VALID if name != "total"}
    perfect = {name: dimension(10) for name in VALID if name != "total"}

    assert CreativeScore.model_validate({**zero, "total": 0.0}).total == 0.0
    assert CreativeScore.model_validate({**perfect, "total": 100.0}).total == 100.0
