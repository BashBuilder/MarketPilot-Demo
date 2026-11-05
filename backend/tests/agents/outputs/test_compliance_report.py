"""Validation tests for ComplianceReport."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.compliance_report import ComplianceReport

VALID = {
    "items": [
        {
            "check": "No guaranteed results",
            "passed": True,
            "reason": "Copy avoids outcome promises.",
        },
        {
            "check": "Medical claims",
            "passed": False,
            "reason": "Headline implies clinical repair.",
        },
    ]
}
INVALID = {"items": []}


def test_valid_report_parses() -> None:
    report = ComplianceReport.model_validate(VALID)

    assert len(report.items) == 2
    assert report.items[1].passed is False


def test_invalid_report_is_rejected() -> None:
    with pytest.raises(ValidationError, match="items"):
        ComplianceReport.model_validate(INVALID)


def test_missing_reason_is_rejected() -> None:
    payload = {"items": [{"check": "Medical claims", "passed": False, "reason": ""}]}

    with pytest.raises(ValidationError, match="reason"):
        ComplianceReport.model_validate(payload)


def test_non_boolean_passed_is_rejected() -> None:
    payload = {
        "items": [{"check": "Medical claims", "passed": "maybe", "reason": "Implied claim."}]
    }

    with pytest.raises(ValidationError, match="passed"):
        ComplianceReport.model_validate(payload)
