"""Supervisor routing: escalation, compliance, score loops and humans."""

import pytest

from app.agents.outputs import ComplianceItem, ComplianceReport, CreativeScore
from app.agents.scoring import DIMENSION_WEIGHTS, weighted_total
from app.agents.supervisor import AUTO_LOOP_KEY, route
from app.core.config import Settings
from app.graph.state import WorkflowState

IDEA = "Create a campaign for a fictional hair-care product"


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        **overrides,
    )


def score(**lowest: float) -> CreativeScore:
    values = {name: 8.0 for name in DIMENSION_WEIGHTS}
    values.update(lowest)
    payload = {
        name: {"score": value, "justification": "Clear rationale for this dimension."}
        for name, value in values.items()
    }
    payload["total"] = weighted_total(values)
    return CreativeScore.model_validate(payload)


def compliance(*items: tuple[str, bool, str]) -> ComplianceReport:
    return ComplianceReport(
        items=[
            ComplianceItem(check=check, passed=passed, reason=reason)
            for check, passed, reason in items
        ]
    )


def state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {"idea": IDEA, "score": score()}
    values.update(overrides)
    return WorkflowState.model_validate(values)


COPY_FAILURE = compliance(("variant 2 (Email): guaranteed results", False, "Remove the guarantee."))
ASSET_FAILURE = compliance(("asset 1: visible watermark", False, "Remove the watermark."))


@pytest.mark.parametrize(
    "error",
    [
        "RetryExhausted: copywriter failed",
        "retry_exhausted",
        "output failed verification after 3 attempts",
        "retry budget exhausted after 3 attempts",
    ],
)
def test_retry_exhausted_escalates_to_human(error: str) -> None:
    decision = route(state(errors=[error]), settings=settings())

    assert decision.next_node == "human"
    assert decision.escalate is True


def test_copy_compliance_failure_routes_to_copywriter() -> None:
    decision = route(state(compliance=COPY_FAILURE), settings=settings())

    assert decision.next_node == "copywriter"
    assert decision.escalate is False


def test_asset_compliance_failure_routes_to_designer() -> None:
    decision = route(state(compliance=ASSET_FAILURE), settings=settings())

    assert decision.next_node == "designer"


def test_copy_failure_wins_when_both_kinds_fail() -> None:
    report = compliance(
        ("asset 1: visible watermark", False, "Remove the watermark."),
        ("variant 1: guaranteed results", False, "Remove the guarantee."),
    )

    assert route(state(compliance=report), settings=settings()).next_node == "copywriter"


def test_retry_exhausted_precedes_compliance() -> None:
    decision = route(
        state(errors=["retry_exhausted"], compliance=COPY_FAILURE),
        settings=settings(),
    )

    assert decision.next_node == "human"
    assert decision.escalate is True


def test_low_score_routes_to_weakest_and_counts_the_loop() -> None:
    workflow = state(score=score(copy_quality=2.0))

    decision = route(workflow, settings=settings(score_threshold=70, max_auto_loops=2))

    assert decision.next_node == "copywriter"
    assert decision.escalate is False
    assert workflow.retry_counters[AUTO_LOOP_KEY] == 1


def test_third_low_score_escalates_instead_of_looping() -> None:
    workflow = state(score=score(copy_quality=2.0))
    limits = settings(score_threshold=70, max_auto_loops=2)

    assert route(workflow, settings=limits).next_node == "copywriter"
    assert route(workflow, settings=limits).next_node == "copywriter"
    decision = route(workflow, settings=limits)

    assert decision.next_node == "human"
    assert decision.escalate is True
    assert workflow.retry_counters[AUTO_LOOP_KEY] == 2


def test_high_score_goes_to_human_gate() -> None:
    decision = route(state(score=score()), settings=settings())

    assert decision.next_node == "human"
    assert decision.escalate is False


def test_human_revise_uses_the_given_target() -> None:
    workflow = state(status="revising", target_node="designer", score=score(copy_quality=2.0))

    decision = route(workflow, settings=settings())

    assert decision.next_node == "designer"
    assert decision.escalate is False


def test_human_revise_without_target_uses_the_weakest_node() -> None:
    workflow = state(status="revising", score=score(visual_quality=2.0))

    assert route(workflow, settings=settings()).next_node == "creative_director"


def test_human_approval_ends_the_run() -> None:
    workflow = state(status="approved", score=score(copy_quality=2.0))

    assert route(workflow, settings=settings()).next_node == "end"
