"""Deterministic payloads that stand in for one run of each agent.

These are fixtures, not model output. The offline gate uses them to prove the
contracts still accept a complete, valid package without calling a provider.
"""

from typing import Final

GOLDEN_OUTPUTS: Final[dict[str, object]] = {
    "brief": {
        "product": "Aurelia Repair Shampoo",
        "goal": "Launch a repair line for colour-treated hair",
        "audience": "Adults aged 25 to 40",
        "tone": "Warm and confident",
        "channels": ["Instagram", "Email"],
        "constraints": ["No medical claims"],
    },
    "research": {
        "segments": [
            {"name": "Colour care", "description": "People with colour-treated hair."},
        ],
        "pain_points": ["Frizz after washing"],
        "messaging_angles": ["Repair without weight"],
        "sources": [
            {
                "url": "https://example.com/research/hair-care-trends",
                "title": "Hair care trends",
            }
        ],
    },
    "copywriter": {
        "variants": [
            {
                "channel": "Instagram",
                "headline": "Repair starts here",
                "description": "A weekly ritual for colour-treated hair.",
                "cta": "Shop now",
            }
        ]
    },
    "creative_director": {
        "image_prompts": ["Soft-lit studio portrait with glossy, natural hair"],
        "video_prompts": ["Slow dolly shot through a sunlit bathroom"],
        "style_guide": "Warm neutrals, editorial calm, no plastic textures",
        "composition": "Rule of thirds with generous negative space",
        "negative_prompts": ["text", "watermark"],
    },
    "designer": {
        "assets": [
            {
                "uri": "hero.png",
                "checksum": "a" * 64,
                "model": "fake",
                "seed": 1,
                "prompt": "Editorial portrait",
            }
        ]
    },
    "compliance": {
        "items": [
            {
                "check": "Medical claims",
                "passed": True,
                "reason": "No medical claims were found in the copy.",
            }
        ]
    },
    "reviewer": {
        "brief_alignment": {"score": 8, "justification": "The brief matches the idea."},
        "audience_fit": {"score": 7, "justification": "The audience is addressed directly."},
        "copy_quality": {"score": 9, "justification": "Copy is specific and free of claims."},
        "visual_quality": {"score": 8, "justification": "The visuals stay on brand."},
        "compliance_risk": {"score": 9, "justification": "No risky claims were found."},
        "total": 82.0,
    },
    "supervisor": {
        "next_node": "end",
        "reason": "The package is ready for the human approval gate.",
    },
}

# Repeated reviewer scores for the same package; a regression widens the spread.
REPEATED_SCORES: Final[tuple[float, ...]] = (82.0, 82.0, 81.5)
MAX_SCORE_SPREAD: Final[float] = 2.0

# Automatic-loop counters recorded at checkpoints across a successful run.
RECORDED_LOOPS: Final[tuple[int, ...]] = (0, 1, 2, 2)
