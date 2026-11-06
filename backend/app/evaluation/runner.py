"""Offline evaluation gate for the campaign pipeline.

No provider, database or network is touched: the golden payloads in
``golden.py`` stand in for agent output and a small keyword reference detector
stands in for the Compliance agent. That keeps the gate deterministic while it
still catches contract drift, dataset gaps and loop or score regressions.
"""

from dataclasses import dataclass
from typing import Final

from app.evaluation.datasets import BAD_CLAIM_CASES, CLEAN_CASES, GOLDEN_IDEAS
from app.evaluation.evaluators import (
    LoopEvent,
    RecallResult,
    compliance_false_positive_rate,
    compliance_recall,
    loop_behavior,
    schema_validity,
    score_spread,
)
from app.evaluation.golden import (
    GOLDEN_OUTPUTS,
    MAX_SCORE_SPREAD,
    RECORDED_LOOPS,
    REPEATED_SCORES,
)

MIN_RECALL: Final[float] = 0.9
MAX_FALSE_POSITIVE_RATE: Final[float] = 0.0

# The reference detector only proves the dataset still covers each rule; it is
# not a model and must never be treated as a compliance verdict in production.
_RULE_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    "guaranteed results": ("guarantee",),
    "instant results": ("instant",),
    "before-and-after promises": ("before-and-after",),
    "miracle or cure wording": ("miracle", "cure"),
    "absolute 100% claim": ("100%",),
    "targeting minors": ("teens", "12"),
    "named real person": ("dr.",),
    "named brand comparison": ("better than", "same formula"),
}


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Every measured metric plus the gate verdict."""

    schema_passed: int
    schema_total: int
    recall: RecallResult
    false_positive_rate: float
    spread: float
    loops_within_cap: bool
    datasets_valid: bool

    @property
    def schema_rate(self) -> float:
        return self.schema_passed / self.schema_total if self.schema_total else 0.0

    @property
    def passed(self) -> bool:
        return (
            self.schema_total > 0
            and self.schema_passed == self.schema_total
            and self.recall.overall >= MIN_RECALL
            and self.false_positive_rate <= MAX_FALSE_POSITIVE_RATE
            and self.spread <= MAX_SCORE_SPREAD
            and self.loops_within_cap
            and self.datasets_valid
        )


def run_evaluation() -> EvaluationReport:
    """Measure every gate; callers decide what to do with a regression."""
    schema = schema_validity(GOLDEN_OUTPUTS)
    return EvaluationReport(
        schema_passed=schema.passed,
        schema_total=schema.total,
        recall=compliance_recall(
            BAD_CLAIM_CASES, {case.id: _reference_flags(case.text) for case in BAD_CLAIM_CASES}
        ),
        false_positive_rate=compliance_false_positive_rate(
            CLEAN_CASES, {case.id: _reference_flags(case.text) for case in CLEAN_CASES}
        ),
        spread=score_spread(REPEATED_SCORES),
        loops_within_cap=loop_behavior(LoopEvent(auto_loops=n) for n in RECORDED_LOOPS),
        datasets_valid=_datasets_are_valid(),
    )


def _reference_flags(text: str) -> bool:
    folded = text.casefold()
    return any(keyword in folded for keywords in _RULE_KEYWORDS.values() for keyword in keywords)


def _datasets_are_valid() -> bool:
    ideas = [idea.idea.strip() for idea in GOLDEN_IDEAS]
    ids = [idea.id for idea in GOLDEN_IDEAS]
    return bool(ideas) and all(ideas) and len(ids) == len(set(ids))


def _print_report(report: EvaluationReport) -> None:
    print(
        f"schema validity: {report.schema_passed}/{report.schema_total} ({report.schema_rate:.1%})"
    )
    print(f"compliance recall: {report.recall.overall:.1%} (minimum {MIN_RECALL:.0%})")
    print(f"compliance false positives: {report.false_positive_rate:.1%}")
    print(f"score spread: {report.spread:.1f} (maximum {MAX_SCORE_SPREAD:.1f})")
    print(f"loop behaviour within cap: {report.loops_within_cap}")
    print(f"datasets valid: {report.datasets_valid}")
    print("evaluation passed" if report.passed else "evaluation FAILED")


def main() -> int:
    """Run the gate and return a shell exit code."""
    report = run_evaluation()
    _print_report(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
