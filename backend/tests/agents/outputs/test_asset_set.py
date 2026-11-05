"""Validation tests for AssetSet."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.asset_set import AssetSet

CHECKSUM = "a" * 64
VALID = {
    "assets": [
        {
            "uri": "s3://marketpilot/assets/hero.png",
            "checksum": CHECKSUM,
            "model": "flux-schnell",
            "seed": 42,
            "prompt": "Editorial portrait in warm light",
        }
    ]
}
INVALID = {
    "assets": [
        {
            **VALID["assets"][0],
            "checksum": "not-a-checksum",
            "prompt": "",
        }
    ]
}


def test_valid_asset_set_parses() -> None:
    assets = AssetSet.model_validate(VALID)

    assert assets.assets[0].seed == 42
    assert assets.assets[0].model == "flux-schnell"


def test_invalid_asset_set_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        AssetSet.model_validate(INVALID)

    message = str(excinfo.value)
    assert "checksum" in message
    assert "prompt" in message


def test_empty_asset_set_is_rejected() -> None:
    with pytest.raises(ValidationError, match="assets"):
        AssetSet.model_validate({"assets": []})


def test_duplicate_asset_uris_are_rejected() -> None:
    payload = {"assets": VALID["assets"] + VALID["assets"]}

    with pytest.raises(ValidationError, match="asset uris must be unique"):
        AssetSet.model_validate(payload)


def test_negative_seed_is_rejected() -> None:
    payload = {"assets": [{**VALID["assets"][0], "seed": -1}]}

    with pytest.raises(ValidationError, match="seed"):
        AssetSet.model_validate(payload)


def test_uri_with_whitespace_is_rejected() -> None:
    payload = {"assets": [{**VALID["assets"][0], "uri": "s3://bucket/my asset.png"}]}

    with pytest.raises(ValidationError, match="uri must not contain whitespace"):
        AssetSet.model_validate(payload)
