"""Validation tests for AudienceResearch."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.audience_research import AudienceResearch

VALID = {
    "segments": [
        {
            "name": "Colour-treated professionals",
            "description": "Busy professionals who colour their hair monthly.",
        },
        {
            "name": "First-time buyers",
            "description": "Shoppers new to reparative hair care.",
        },
    ],
    "pain_points": ["Frizz after washing", "Colour fading quickly"],
    "messaging_angles": ["Repair without weighing hair down", "Colour that lasts"],
    "sources": [
        {
            "url": "https://example.com/research/hair-care-trends",
            "title": "Hair care trends: scalp-first routines",
        }
    ],
}

INVALID = {
    **VALID,
    "segments": [],
    "pain_points": [""],
}


def test_valid_research_parses() -> None:
    research = AudienceResearch.model_validate(VALID)

    assert len(research.segments) == 2
    assert research.messaging_angles[0] == "Repair without weighing hair down"
    assert str(research.sources[0].url) == "https://example.com/research/hair-care-trends"


def test_invalid_research_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        AudienceResearch.model_validate(INVALID)

    message = str(excinfo.value)
    assert "segments" in message
    assert "pain_points" in message


def test_duplicate_segment_names_are_rejected() -> None:
    payload = {
        **VALID,
        "segments": [
            {"name": "Professionals", "description": "Busy professionals."},
            {"name": "professionals", "description": "Another description."},
        ],
    }

    with pytest.raises(ValidationError, match="segment names must be unique"):
        AudienceResearch.model_validate(payload)


def test_short_segment_description_is_rejected() -> None:
    payload = {
        **VALID,
        "segments": [{"name": "Professionals", "description": "Busy"}],
    }

    with pytest.raises(ValidationError, match="description"):
        AudienceResearch.model_validate(payload)


def test_empty_sources_are_rejected() -> None:
    with pytest.raises(ValidationError, match="sources"):
        AudienceResearch.model_validate({**VALID, "sources": []})


def test_invalid_source_url_is_rejected() -> None:
    payload = {
        **VALID,
        "sources": [{"url": "not-a-url", "title": "Invented source"}],
    }

    with pytest.raises(ValidationError, match="url"):
        AudienceResearch.model_validate(payload)
