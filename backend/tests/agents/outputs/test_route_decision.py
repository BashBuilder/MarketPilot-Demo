"""Validation tests for RouteDecision."""

import pytest
from pydantic import ValidationError

from app.agents.outputs.route_decision import RouteDecision

VALID = {
    "next_node": "compliance",
    "reason": "Copy is ready for a policy check.",
}


def test_valid_decision_parses() -> None:
    decision = RouteDecision.model_validate(VALID)

    assert decision.next_node == "compliance"
    assert decision.escalate is False


def test_invalid_decision_is_rejected() -> None:
    payload = {**VALID, "next_node": "supervisor", "reason": "no"}

    with pytest.raises(ValidationError) as excinfo:
        RouteDecision.model_validate(payload)

    message = str(excinfo.value)
    assert "next_node" in message
    assert "reason" in message


def test_escalation_target_is_allowed() -> None:
    decision = RouteDecision.model_validate({**VALID, "next_node": "human", "escalate": True})

    assert decision.next_node == "human"
    assert decision.escalate is True


def test_non_boolean_escalate_is_rejected() -> None:
    with pytest.raises(ValidationError, match="escalate"):
        RouteDecision.model_validate({**VALID, "escalate": "maybe"})


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="tool"):
        RouteDecision.model_validate({**VALID, "tool": "export_package"})
