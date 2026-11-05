"""Tests for per-agent context slicing and token budgeting."""

import pytest
from context_support import PACKAGE_FIELDS, long_state, state

from app.core.errors import ContextBudgetExceeded
from app.harness.context import (
    AGENT_CONTEXT_FIELDS,
    build_agent_context,
    estimate_context_tokens,
    estimate_tokens,
)
from app.harness.registry import AgentName


@pytest.mark.parametrize("agent", sorted(AGENT_CONTEXT_FIELDS))
def test_agent_receives_only_mapped_fields(agent: AgentName) -> None:
    source = state()
    context = build_agent_context(source, agent, budget=100_000)

    assert context.idea == source.idea
    for field in PACKAGE_FIELDS:
        if field in AGENT_CONTEXT_FIELDS[agent]:
            assert getattr(context, field) == getattr(source, field)
        else:
            assert getattr(context, field) is None

    if agent == "supervisor":
        assert context.status == source.status
        assert context.retry_counters == source.retry_counters
        assert context.errors == source.errors
    else:
        assert context.status == "pending"
        assert context.retry_counters == {}
        assert context.errors == []


def test_mapping_matches_agent_responsibilities() -> None:
    assert AGENT_CONTEXT_FIELDS["copywriter"] == frozenset(
        {"brief", "research", "copy", "revision_feedback"}
    )
    assert AGENT_CONTEXT_FIELDS["designer"] == frozenset(
        {"direction", "assets", "revision_feedback"}
    )
    assert AGENT_CONTEXT_FIELDS["reviewer"] == frozenset(PACKAGE_FIELDS) | {"revision_feedback"}


def test_revision_feedback_and_own_output_are_mapped() -> None:
    source = state(revision_feedback="Tighten the claims")
    context = build_agent_context(source, "copywriter", budget=100_000)

    assert context.revision_feedback == "Tighten the claims"
    assert context.copy == source.copy


def test_long_fixture_stays_under_budget_and_keeps_protected_fields() -> None:
    source = long_state()
    budget = 3_000

    context = build_agent_context(source, "reviewer", budget)

    assert estimate_context_tokens(context) <= budget
    assert context.brief == source.brief
    assert context.compliance == source.compliance
    assert context.research is not None
    assert len(context.research.segments) == 1
    assert context.direction is not None
    assert context.direction.style_guide != source.direction.style_guide


def test_research_is_trimmed_before_free_text() -> None:
    source = long_state()
    assert source.research is not None
    reduced = source.model_copy(
        update={
            "research": source.research.model_copy(
                update={
                    "segments": source.research.segments[-1:],
                    "pain_points": source.research.pain_points[-1:],
                    "messaging_angles": source.research.messaging_angles[-1:],
                }
            )
        }
    )
    budget = estimate_context_tokens(build_agent_context(reduced, "reviewer", 10_000_000))

    context = build_agent_context(source, "reviewer", budget)

    assert context.research == reduced.research
    assert context.direction == source.direction


def test_injected_estimator_controls_trimming() -> None:
    source = long_state()

    context = build_agent_context(source, "reviewer", budget=1, estimate=lambda _: 0)

    assert context.research is not None
    assert len(context.research.segments) == 40


def test_protected_fields_that_cannot_fit_raise() -> None:
    with pytest.raises(ContextBudgetExceeded):
        build_agent_context(state(), "brief", budget=1)


def test_estimate_tokens_is_character_based() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2
