"""Named people and brands the Creative Director must not reference.

Keep entries lower-case and one per line. Matching is case-insensitive and
word-boundary based, so add the exact name or brand to block.
"""

BLOCKED_NAMES: frozenset[str] = frozenset(
    {
        "taylor swift",
        "beyonce",
        "cristiano ronaldo",
        "elon musk",
        "coca-cola",
        "nike",
        "gucci",
        "disney",
        "marvel",
        "apple",
    }
)
