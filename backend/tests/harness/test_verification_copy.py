"""Schema and semantic verification for advertising copy."""

from app.agents.outputs import AdCopySet
from app.agents.outputs.ad_copy_set import CopyVariant
from app.harness.verification import CopySemanticValidator, verify_output

VALID_PAYLOAD = {
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
    ]
}


def test_clean_copy_passes_both_layers() -> None:
    parsed, issues = verify_output(AdCopySet, VALID_PAYLOAD, CopySemanticValidator())

    assert isinstance(parsed, AdCopySet)
    assert issues == []


def test_schema_failure_short_circuits_the_semantic_layer() -> None:
    parsed, issues = verify_output(AdCopySet, {"variants": []}, CopySemanticValidator())

    assert parsed is None
    assert len(issues) == 1
    assert "variants" in issues[0]


def test_empty_variant_fields_are_reported() -> None:
    blank = CopyVariant.model_construct(channel="Email", headline="", description="", cta="")
    copy = AdCopySet.model_construct(variants=[blank])

    issues = CopySemanticValidator().validate(copy)

    assert any("variant 1 (Email): headline is empty" in issue for issue in issues)
    assert any("description is empty" in issue for issue in issues)
    assert any("cta is empty" in issue for issue in issues)


def test_over_long_headline_reports_the_limit() -> None:
    payload = {
        "variants": [
            {
                "channel": "Instagram",
                "headline": "x" * 41,
                "description": "A weekly ritual for colour-treated hair.",
                "cta": "Shop now",
            }
        ]
    }
    parsed = AdCopySet.model_validate(payload)

    issues = CopySemanticValidator().validate(parsed)

    assert issues == ["variant 1 (Instagram): headline is 41 characters; limit is 40"]
