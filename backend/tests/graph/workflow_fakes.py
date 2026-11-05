"""Scripted LLM payloads for the linear workflow integration test."""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from app.agents.contracts import ChatMessage

IDEA = "Create an advertising campaign for a fictional hair-care product"

BRIEF: dict[str, Any] = {
    "product": "Aurelia Repair Shampoo",
    "goal": "Launch a repair line for colour-treated hair",
    "audience": "Adults aged 25 to 40",
    "tone": "Warm and confident",
    "channels": ["Instagram", "Email"],
    "constraints": ["No medical claims"],
}

RESEARCH: dict[str, Any] = {
    "segments": [
        {
            "name": "Colour-treated professionals",
            "description": "Busy professionals who colour their hair monthly.",
        }
    ],
    "pain_points": ["Frizz after washing"],
    "messaging_angles": ["Repair without weighing hair down"],
    "sources": [
        {
            "url": "https://example.com/research/hair-care-trends",
            "title": "Hair care trends: scalp-first routines",
        },
        {
            "url": "https://example.com/research/audience-messaging",
            "title": "Audience messaging for everyday personal care",
        },
    ],
}

COPY: dict[str, Any] = {
    "variants": [
        {
            "channel": "Instagram",
            "headline": "Repair starts here",
            "description": "A weekly ritual for colour-treated hair.",
            "cta": "Shop now",
        },
        {
            "channel": "Email",
            "headline": "Your hair, softer",
            "description": "A gentle routine for colour-treated hair.",
            "cta": "Learn more",
        },
    ]
}

DIRECTION: dict[str, Any] = {
    "image_prompts": ["Soft-lit studio portrait with glossy, natural hair"],
    "video_prompts": ["Slow dolly shot through a sunlit bathroom"],
    "style_guide": "Warm neutrals, editorial calm, no plastic textures",
    "composition": "Rule of thirds with generous negative space on the right",
    "negative_prompts": ["text", "watermark"],
}

COMPLIANCE: dict[str, Any] = {
    "items": [
        {
            "check": "Medical claims",
            "passed": True,
            "reason": "No medical or therapeutic claims were found.",
        }
    ]
}

SCORE: dict[str, Any] = {
    "brief_alignment": {"score": 8, "justification": "Follows the brief closely."},
    "audience_fit": {"score": 7, "justification": "Speaks to colour-treated hair."},
    "copy_quality": {"score": 9, "justification": "Clear, specific and persuasive."},
    "visual_quality": {"score": 8, "justification": "Consistent with the warm direction."},
    "compliance_risk": {"score": 9, "justification": "No unresolved claim risks."},
    "total": 82.0,
}

PAYLOADS: tuple[dict[str, Any], ...] = (BRIEF, RESEARCH, COPY, DIRECTION, COMPLIANCE, SCORE)


class FakeWorkflowLLM:
    """Return payloads in call order and fail loudly if the script runs out."""

    def __init__(self, payloads: Sequence[dict[str, Any]] = PAYLOADS) -> None:
        self._payloads = list(payloads)
        self.calls = 0

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[BaseModel],
    ) -> Any:
        del messages, schema
        payload = self._payloads[self.calls]
        self.calls += 1
        return payload
