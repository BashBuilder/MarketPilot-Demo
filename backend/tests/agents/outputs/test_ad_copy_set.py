"""Validation tests for AdCopySet."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.ad_copy_set import AdCopySet

VALID = {
    "variants": [
        {
            "channel": "Instagram",
            "headline": "Repair starts here",
            "description": "A weekly ritual for colour-treated hair.",
            "cta": "Shop now",
        },
        {
            "channel": "Email",
            "headline": "Your hair, restored",
            "description": "Meet the repair line built for busy mornings.",
            "cta": "Learn more",
        },
    ],
}

INVALID = {
    "variants": [
        {
            "channel": "X",
            "headline": "Hi",
            "description": "Too short",
            "cta": "",
        }
    ]
}


def test_valid_copy_set_parses() -> None:
    copy = AdCopySet.model_validate(VALID)

    assert len(copy.variants) == 2
    assert copy.variants[0].channel == "Instagram"


def test_invalid_copy_set_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        AdCopySet.model_validate(INVALID)

    message = str(excinfo.value)
    for field in ("channel", "headline", "description", "cta"):
        assert field in message


def test_empty_variants_are_rejected() -> None:
    with pytest.raises(ValidationError, match="variants"):
        AdCopySet.model_validate({"variants": []})


def test_duplicate_variant_is_rejected() -> None:
    payload = {"variants": VALID["variants"] + VALID["variants"]}

    with pytest.raises(ValidationError, match="duplicate variant"):
        AdCopySet.model_validate(payload)
