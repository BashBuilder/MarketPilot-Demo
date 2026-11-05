"""Field-level version diffs over every campaign package section."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

from app.database.models import CampaignVersion
from app.graph.diff import compute_diff
from app.graph.versioning import PACKAGE_FIELDS

BASE: dict[str, Any] = {
    "brief": {"product": "Aurelia", "constraints": ["No medical claims"]},
    "research": {
        "segments": [{"name": "Colour care", "description": "Colour-treated hair."}],
        "pain_points": ["Frizz"],
    },
    "copy": {
        "variants": [
            {
                "channel": "Instagram",
                "headline": "Repair starts here",
                "description": "A weekly ritual.",
                "cta": "Shop now",
            }
        ]
    },
    "direction": {"image_prompts": ["Soft light"], "negative_prompts": ["text"]},
    "assets": {
        "assets": [
            {
                "uri": "assets/a.png",
                "checksum": "a" * 64,
                "model": "fake",
                "seed": 1,
                "prompt": "portrait",
            }
        ]
    },
    "compliance": {"items": [{"check": "Claims", "passed": True, "reason": "None found."}]},
    "score": {"brief_alignment": {"score": 8, "justification": "Aligned"}, "total": 76.0},
}


def _version(number: int, package: dict[str, Any]) -> CampaignVersion:
    return CampaignVersion(campaign_id=uuid4(), version=number, package=package)


def test_identical_versions_have_no_changes() -> None:
    diff = compute_diff(_version(1, BASE), _version(1, deepcopy(BASE)))

    assert diff == {"from": 1, "to": 1, "changes": []}


def test_changes_cover_every_package_section_with_dotted_paths() -> None:
    assert set(BASE) == set(PACKAGE_FIELDS)
    after = deepcopy(BASE)
    after["brief"]["product"] = "Aurelia Repair"
    after["research"]["segments"][0]["name"] = "Colour-treated"
    after["copy"]["variants"][0]["headline"] = "A gentler weekly ritual"
    after["direction"]["image_prompts"][0] = "Editorial portrait"
    after["assets"]["assets"][0]["seed"] = 2
    after["compliance"]["items"][0]["passed"] = False
    after["score"]["total"] = 82.0

    diff = compute_diff(_version(1, BASE), _version(2, after))

    assert diff["from"] == 1
    assert diff["to"] == 2
    assert {change["path"] for change in diff["changes"]} == {
        "brief.product",
        "research.segments.0.name",
        "copy.variants.0.headline",
        "direction.image_prompts.0",
        "assets.assets.0.seed",
        "compliance.items.0.passed",
        "score.total",
    }
    headline = next(
        change for change in diff["changes"] if change["path"] == "copy.variants.0.headline"
    )
    assert headline["before"] == "Repair starts here"
    assert headline["after"] == "A gentler weekly ritual"
