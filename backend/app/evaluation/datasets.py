"""Golden campaign ideas and compliance fixtures used by offline evaluation runs."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldenIdea:
    """One reproducible campaign prompt for evaluation."""

    id: str
    idea: str
    target_age_range: str
    channel_hints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BadClaimCase:
    """A copy variant that compliance must reject."""

    id: str
    text: str
    violated_rule: str


@dataclass(frozen=True, slots=True)
class CleanCase:
    """A copy variant that compliance must pass."""

    id: str
    text: str


HAIR_CARE_IDEA = (
    "Create an advertising campaign for a fictional hair-care product "
    "targeting adults aged 25 to 40."
)

GOLDEN_IDEAS: tuple[GoldenIdea, ...] = (
    GoldenIdea(
        "idea-hair-care-adults-25-40",
        HAIR_CARE_IDEA,
        "25-40",
        ("Instagram", "Email"),
    ),
    GoldenIdea(
        "idea-plant-snack-students-18-24",
        "Create a campaign for a fictional plant-based snack brand aimed at "
        "university students aged 18 to 24.",
        "18-24",
        ("TikTok", "Campus radio"),
    ),
    GoldenIdea(
        "idea-desk-lamp-remote-workers-30-50",
        "Create a campaign for a fictional ergonomic desk lamp aimed at "
        "remote workers aged 30 to 50.",
        "30-50",
        ("LinkedIn", "Podcast"),
    ),
    GoldenIdea(
        "idea-water-bottle-hikers-25-45",
        "Create a campaign for a fictional refillable water bottle aimed at "
        "outdoor hikers aged 25 to 45.",
        "25-45",
        ("Instagram", "YouTube"),
    ),
    GoldenIdea(
        "idea-pet-mitt-cat-owners-30-55",
        "Create a campaign for a fictional pet grooming mitt aimed at cat owners aged 30 to 55.",
        "30-55",
        ("Facebook", "Pinterest"),
    ),
    GoldenIdea(
        "idea-budget-app-young-families-25-40",
        "Create a campaign for a fictional budgeting app aimed at young families aged 25 to 40.",
        "25-40",
        ("YouTube", "Email"),
    ),
)

BAD_CLAIM_CASES: tuple[BadClaimCase, ...] = (
    BadClaimCase("bad-guarantee-1", "Veyra guarantees results in 14 days.", "guaranteed results"),
    BadClaimCase("bad-guarantee-2", "Mossling guarantees clear skin.", "guaranteed results"),
    BadClaimCase("bad-instant-1", "Silkfern gives instant salon shine.", "instant results"),
    BadClaimCase("bad-before-1", "Before-and-after glow in 7 days.", "before-and-after promises"),
    BadClaimCase("bad-miracle-1", "A miracle cure for thinning hair.", "miracle or cure wording"),
    BadClaimCase("bad-cure-1", "Proven to cure dandruff forever.", "miracle or cure wording"),
    BadClaimCase("bad-absolute-1", "100% of users saw thicker hair.", "absolute 100% claim"),
    BadClaimCase("bad-absolute-2", "100% risk-free and 100% effective.", "absolute 100% claim"),
    BadClaimCase("bad-minors-1", "Perfect for teens as young as 12.", "targeting minors"),
    BadClaimCase("bad-person-1", "Dr. Vela Nunez guarantees this works.", "named real person"),
    BadClaimCase("bad-brand-1", "Better than Zentra Beauty.", "named brand comparison"),
    BadClaimCase("bad-brand-2", "Same formula as GlowCorp, cheaper.", "named brand comparison"),
)

CLEAN_CASES: tuple[CleanCase, ...] = (
    CleanCase(
        "clean-moisturizer-1", "A lightweight daily moisturizer that helps keep skin feeling soft."
    ),
    CleanCase(
        "clean-shampoo-1", "A gentle shampoo designed to leave hair feeling clean and manageable."
    ),
    CleanCase("clean-snack-1", "A plant-based snack with 6 grams of protein per serving."),
    CleanCase("clean-bottle-1", "A refillable bottle that helps keep water cold for hours."),
    CleanCase("clean-lamp-1", "An adjustable desk lamp with three brightness settings."),
    CleanCase(
        "clean-pet-mitt-1", "A soft grooming mitt that helps reduce loose fur around the home."
    ),
    CleanCase("clean-budget-app-1", "A budgeting app that helps you track everyday spending."),
    CleanCase("clean-cleanser-1", "A gentle cleanser suitable for daily use."),
)
