"""Tests for the schema-validity evaluation metric."""

from app.evaluation.evaluators import SchemaValidity, schema_validity

VALID_SUPERVISOR = {
    "next_node": "end",
    "reason": "The package is ready for the human approval gate.",
}
VALID_COPY = {
    "variants": [
        {
            "channel": "Email",
            "headline": "A calmer morning",
            "description": "A gentle start for every day.",
            "cta": "Learn more",
        }
    ]
}


def test_empty_input_has_no_passes_or_failures() -> None:
    assert schema_validity({}) == SchemaValidity(passed=0, total=0, failing_agents=())


def test_all_valid_outputs_pass() -> None:
    result = schema_validity({"supervisor": VALID_SUPERVISOR, "copywriter": VALID_COPY})

    assert result == SchemaValidity(passed=2, total=2, failing_agents=())


def test_all_invalid_outputs_fail() -> None:
    result = schema_validity({"supervisor": {}, "not-an-agent": {}})

    assert result.passed == 0
    assert result.total == 2
    assert result.failing_agents == ("not-an-agent", "supervisor")


def test_valid_and_invalid_outputs_are_counted_separately() -> None:
    result = schema_validity({"supervisor": VALID_SUPERVISOR, "copywriter": {}})

    assert result == SchemaValidity(passed=1, total=2, failing_agents=("copywriter",))
