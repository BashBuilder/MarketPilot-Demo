"""Golden campaign ideas used by offline evaluation runs."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldenIdea:
    """One reproducible campaign prompt for evaluation."""

    id: str
    idea: str


HAIR_CARE_IDEA = (
    "Create an advertising campaign for a fictional hair-care product "
    "targeting adults aged 25 to 40."
)

GOLDEN_IDEAS: tuple[GoldenIdea, ...] = (
    GoldenIdea(id="hair-care-adults-25-40", idea=HAIR_CARE_IDEA),
)
