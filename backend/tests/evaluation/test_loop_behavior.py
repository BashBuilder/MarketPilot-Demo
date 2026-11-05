"""Tests for automatic-loop behavior evaluation."""

from app.evaluation.evaluators import MAX_AUTO_LOOPS, LoopEvent, loop_behavior


def test_empty_events_are_within_budget() -> None:
    assert loop_behavior([]) is True


def test_events_at_the_limit_are_allowed() -> None:
    events = [LoopEvent(auto_loops=0), LoopEvent(auto_loops=MAX_AUTO_LOOPS)]

    assert loop_behavior(events) is True


def test_any_event_over_the_limit_fails() -> None:
    events = [LoopEvent(auto_loops=1), LoopEvent(auto_loops=MAX_AUTO_LOOPS + 1)]

    assert loop_behavior(events) is False


def test_explicit_limit_overrides_the_default() -> None:
    events = [LoopEvent(auto_loops=1)]

    assert loop_behavior(events, max_auto_loops=0) is False
    assert loop_behavior(events, max_auto_loops=1) is True
