"""Pure scoring helpers for the Reviewer's rubric."""

import pytest

from app.agents.outputs import CreativeScore
from app.agents.scoring import DIMENSION_WEIGHTS, weakest_node, weighted_total


def make_score(**lowest: float) -> CreativeScore:
    scores = {name: 8.0 for name in DIMENSION_WEIGHTS}
    scores.update(lowest)
    payload = {
        name: {"score": value, "justification": "Clear rationale for this dimension."}
        for name, value in scores.items()
    }
    payload["total"] = weighted_total(scores)
    return CreativeScore.model_validate(payload)


def test_weighted_total_uses_the_rubric() -> None:
    assert weighted_total({name: 8.0 for name in DIMENSION_WEIGHTS}) == 80.0
    assert weighted_total({name: 0.0 for name in DIMENSION_WEIGHTS}) == 0.0
    assert weighted_total({name: 10.0 for name in DIMENSION_WEIGHTS}) == 100.0


def test_weighted_total_rejects_missing_or_out_of_range() -> None:
    with pytest.raises(ValueError, match="missing dimensions"):
        weighted_total({"brief_alignment": 5.0})
    with pytest.raises(ValueError, match="between 0 and 10"):
        weighted_total({name: 11.0 for name in DIMENSION_WEIGHTS})


@pytest.mark.parametrize(
    ("dimension", "node"),
    [
        ("brief_alignment", "brief"),
        ("audience_fit", "research"),
        ("copy_quality", "copywriter"),
        ("visual_quality", "creative_director"),
        ("compliance_risk", "copywriter"),
    ],
)
def test_weakest_node_covers_every_dimension(dimension: str, node: str) -> None:
    assert weakest_node(make_score(**{dimension: 2.0})) == node


def test_ties_pick_the_earlier_pipeline_node() -> None:
    # Research runs after Brief.
    assert weakest_node(make_score(brief_alignment=2.0, audience_fit=2.0)) == "brief"
    # Copywriter runs before Creative Director, so compliance risk wins the tie.
    assert weakest_node(make_score(compliance_risk=2.0, visual_quality=2.0)) == "copywriter"
