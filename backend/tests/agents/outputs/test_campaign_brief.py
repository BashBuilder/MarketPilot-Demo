"""Validation tests for CampaignBrief."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.campaign_brief import CampaignBrief

VALID = {
    "product": "Aurelia Repair Shampoo",
    "goal": "Launch a repair line for adults aged 25 to 40",
    "audience": "Adults aged 25 to 40 with colour-treated hair",
    "tone": "Warm and confident",
    "channels": ["Instagram", "Email"],
    "constraints": ["No medical claims", "No guaranteed results"],
}

INVALID = {
    **VALID,
    "product": "A",
    "channels": [],
}


def test_valid_brief_parses() -> None:
    brief = CampaignBrief.model_validate(VALID)

    assert brief.product == "Aurelia Repair Shampoo"
    assert brief.channels == ["Instagram", "Email"]


def test_invalid_brief_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CampaignBrief.model_validate(INVALID)

    message = str(excinfo.value)
    assert "product" in message
    assert "channels" in message


def test_duplicate_channels_are_rejected() -> None:
    payload = {**VALID, "channels": ["Email", "email"]}

    with pytest.raises(ValidationError, match="duplicate list item"):
        CampaignBrief.model_validate(payload)


def test_extra_fields_are_rejected() -> None:
    payload = {**VALID, "secret_claim": "guaranteed results"}

    with pytest.raises(ValidationError, match="secret_claim"):
        CampaignBrief.model_validate(payload)
