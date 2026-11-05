"""Validation tests for CreativeDirection."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.creative_direction import CreativeDirection

VALID = {
    "image_prompts": ["Soft-lit studio portrait of a woman with glossy hair"],
    "video_prompts": ["Slow dolly shot through a sunlit bathroom"],
    "style_guide": "Warm neutrals, editorial calm, no glossy plastic textures",
    "composition": "Rule of thirds with generous negative space on the right",
    "negative_prompts": ["text", "watermark", "distorted hands"],
}

INVALID = {
    **VALID,
    "style_guide": "Warm",
    "negative_prompts": [],
}


def test_valid_direction_parses() -> None:
    direction = CreativeDirection.model_validate(VALID)

    assert direction.image_prompts[0].startswith("Soft-lit")
    assert "watermark" in direction.negative_prompts


def test_invalid_direction_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CreativeDirection.model_validate(INVALID)

    message = str(excinfo.value)
    assert "style_guide" in message
    assert "negative_prompts" in message


def test_duplicate_prompts_are_rejected() -> None:
    payload = {**VALID, "image_prompts": ["Studio portrait", "studio portrait"]}

    with pytest.raises(ValidationError, match="duplicate list item"):
        CreativeDirection.model_validate(payload)


def test_blank_prompt_is_rejected() -> None:
    payload = {**VALID, "video_prompts": ["   "]}

    with pytest.raises(ValidationError, match="video_prompts"):
        CreativeDirection.model_validate(payload)
