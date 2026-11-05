"""Pure scoring helpers for the Reviewer's five-dimension rubric.

The dimensions are equally weighted and each is scored 0 to 10, so the total
is out of 100. Keeping the formula and the rerun mapping here means the output
model, the agent validator and the tests all read the same rubric.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from app.agents.outputs.creative_score import CreativeScore
    from app.agents.outputs.route_decision import AgentNode

DIMENSION_WEIGHTS: Final[dict[str, float]] = {
    "brief_alignment": 0.2,
    "audience_fit": 0.2,
    "copy_quality": 0.2,
    "visual_quality": 0.2,
    "compliance_risk": 0.2,
}

DIMENSION_NODES: Final[dict[str, AgentNode]] = {
    "brief_alignment": "brief",
    "audience_fit": "research",
    "copy_quality": "copywriter",
    "visual_quality": "creative_director",
    "compliance_risk": "copywriter",
}

_DIMENSION_ORDER: Final[tuple[str, ...]] = tuple(DIMENSION_WEIGHTS)
_NODE_ORDER: Final[tuple[str, ...]] = (
    "brief",
    "research",
    "copywriter",
    "creative_director",
    "designer",
    "compliance",
    "reviewer",
)
_NODE_RANK: Final[dict[str, int]] = {node: index for index, node in enumerate(_NODE_ORDER)}


def weighted_total(dimensions: Mapping[str, float]) -> float:
    """Return the rubric total out of 100 for the five dimension scores."""
    missing = [name for name in DIMENSION_WEIGHTS if name not in dimensions]
    if missing:
        raise ValueError(f"missing dimensions: {', '.join(missing)}")

    scores: dict[str, float] = {}
    for name in DIMENSION_WEIGHTS:
        score = dimensions[name]
        if not 0 <= score <= 10:
            raise ValueError(f"{name} must be between 0 and 10")
        scores[name] = score

    weighted = sum(scores[name] * weight for name, weight in DIMENSION_WEIGHTS.items())
    return round(weighted * 10, 2)


def weakest_node(score: CreativeScore) -> AgentNode:
    """Map the lowest-scoring dimension to the node that should rerun.

    Ties resolve to the earlier pipeline node, so a tie between compliance risk
    and visual quality sends the package back to the Copywriter rather than the
    Creative Director.
    """
    dimensions = {
        "brief_alignment": score.brief_alignment.score,
        "audience_fit": score.audience_fit.score,
        "copy_quality": score.copy_quality.score,
        "visual_quality": score.visual_quality.score,
        "compliance_risk": score.compliance_risk.score,
    }
    lowest = min(dimensions.values())
    candidates = [name for name, value in dimensions.items() if value == lowest]
    return DIMENSION_NODES[min(candidates, key=_tie_key)]


def _tie_key(name: str) -> tuple[int, int]:
    return (_NODE_RANK[DIMENSION_NODES[name]], _DIMENSION_ORDER.index(name))
