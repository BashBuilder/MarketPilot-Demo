"""Tests that malformed agent output becomes ValidationFailure."""

from typing import Any

import pytest

from app.agents.outputs import CampaignBrief, CreativeScore
from app.core.errors import ValidationFailure
from app.graph.state import parse_agent_output

VALID_BRIEF: dict[str, Any] = {
    "product": "Aurelia Repair Shampoo",
    "goal": "Launch a repair line for adults",
    "audience": "Adults aged 25 to 40",
    "tone": "Warm and confident",
    "channels": ["Instagram"],
    "constraints": ["No medical claims"],
}
INVALID_BRIEF = {**VALID_BRIEF, "channels": []}


def test_valid_output_returns_model() -> None:
    brief = parse_agent_output(CampaignBrief, VALID_BRIEF, agent="brief")

    assert isinstance(brief, CampaignBrief)
    assert brief.channels == ["Instagram"]


def test_invalid_output_raises_validation_failure() -> None:
    with pytest.raises(ValidationFailure) as excinfo:
        parse_agent_output(CampaignBrief, INVALID_BRIEF, agent="brief")

    error = excinfo.value
    assert error.code == "validation_failed"
    assert error.details["agent"] == "brief"
    fields = [item["field"] for item in error.details["errors"]]
    assert any("channels" in field for field in fields)


def test_score_total_mismatch_raises_validation_failure() -> None:
    def dimension(score: float) -> dict[str, object]:
        return {"score": score, "justification": "Clear rationale."}

    payload = {
        "brief_alignment": dimension(8),
        "audience_fit": dimension(7),
        "copy_quality": dimension(9),
        "visual_quality": dimension(8),
        "compliance_risk": dimension(6),
        "total": 90.0,
    }

    with pytest.raises(ValidationFailure, match="reviewer") as excinfo:
        parse_agent_output(CreativeScore, payload, agent="reviewer")

    assert "total" in str(excinfo.value.details)
