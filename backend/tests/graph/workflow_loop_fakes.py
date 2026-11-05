"""Scripted agents and state fixtures for supervised-loop integration tests."""

from collections.abc import Sequence
from typing import Any

from app.agents.outputs import (
    AdCopySet,
    Asset,
    AssetSet,
    AudienceResearch,
    CampaignBrief,
    ComplianceItem,
    ComplianceReport,
    CreativeDirection,
    CreativeScore,
)
from app.core.errors import RetryExhausted

IDEA = "Create an advertising campaign for a fictional hair-care product"

BRIEF = CampaignBrief(
    product="Aurelia Repair Shampoo",
    goal="Launch a repair line for colour-treated hair",
    audience="Adults aged 25 to 40",
    tone="Warm and confident",
    channels=["Instagram", "Email"],
    constraints=["No medical claims"],
)

RESEARCH = AudienceResearch(
    segments=[{"name": "Colour care", "description": "People with colour-treated hair."}],
    pain_points=["Frizz after washing"],
    messaging_angles=["Repair without weight"],
    sources=[
        {
            "url": "https://example.com/research/hair-care-trends",
            "title": "Hair care trends",
        }
    ],
)

COPY = AdCopySet(
    variants=[
        {
            "channel": "Instagram",
            "headline": "Repair starts here",
            "description": "A weekly ritual for colour-treated hair.",
            "cta": "Shop now",
        }
    ]
)

REVISED_COPY = AdCopySet(
    variants=[
        {
            "channel": "Instagram",
            "headline": "A gentler weekly ritual",
            "description": "Care for colour-treated hair without guarantees.",
            "cta": "See the routine",
        }
    ]
)

DIRECTION = CreativeDirection(
    image_prompts=["Soft-lit studio portrait with glossy, natural hair"],
    video_prompts=["Slow dolly shot through a sunlit bathroom"],
    style_guide="Warm neutrals, editorial calm, no plastic textures",
    composition="Rule of thirds with generous negative space",
    negative_prompts=["text", "watermark"],
)

ASSETS = AssetSet(
    assets=[
        Asset(
            uri="assets/fake.png",
            checksum="a" * 64,
            model="fake",
            seed=1,
            prompt="Editorial portrait",
        )
    ]
)

PASS_REPORT = ComplianceReport(
    items=[
        ComplianceItem(
            check="Medical claims",
            passed=True,
            reason="No medical claims were found in the copy.",
        )
    ]
)

FAIL_COPY_REPORT = ComplianceReport(
    items=[
        ComplianceItem(
            check="Copy variant 1 (Instagram): guaranteed results",
            passed=False,
            reason="Remove the guaranteed-results claim from this copy.",
        )
    ]
)


def score(copy_quality: int = 9) -> CreativeScore:
    """Build a score whose weakest dimension is copy quality when it is low."""
    values = {
        "brief_alignment": 8,
        "audience_fit": 7,
        "copy_quality": copy_quality,
        "visual_quality": 8,
        "compliance_risk": 9,
    }
    dimensions: dict[str, Any] = {
        name: {"score": value, "justification": f"{name} is scored {value}."}
        for name, value in values.items()
    }
    return CreativeScore(**dimensions, total=sum(values.values()) / len(values) * 10)


class ScriptedAgent:
    """Return scripted outputs in order, repeating the last one."""

    context_budget = 4000

    def __init__(
        self,
        name: str,
        outputs: Sequence[Any] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self.outputs = list(outputs)
        self.error = error
        self.calls = 0

    async def run(
        self,
        state: Any,
        llm: object,
        emit: object = None,
        tools: object = None,
        *,
        settings: object = None,
    ) -> Any:
        del state, llm, emit, tools, settings
        self.calls += 1
        if self.error is not None:
            raise self.error
        if not self.outputs:
            raise RetryExhausted(f"{self.name} has no scripted output")
        return self.outputs[min(self.calls - 1, len(self.outputs) - 1)]


def default_agents() -> dict[str, ScriptedAgent]:
    return {
        "brief": ScriptedAgent("brief", [BRIEF]),
        "research": ScriptedAgent("research", [RESEARCH]),
        "copywriter": ScriptedAgent("copywriter", [COPY]),
        "creative_director": ScriptedAgent("creative_director", [DIRECTION]),
        "designer": ScriptedAgent("designer", [ASSETS]),
        "compliance": ScriptedAgent("compliance", [PASS_REPORT]),
        "reviewer": ScriptedAgent("reviewer", [score()]),
    }
