"""Copywriter test data: brief, research, copy and policy fixtures."""

from typing import Any
from uuid import UUID

from app.agents.outputs import (
    AudienceResearch,
    CampaignBrief,
    ComplianceItem,
    ComplianceReport,
)
from app.tools.policy_models import PolicyMatch

IDEA = "Create a campaign for a fictional hair-care product"

BRIEF = CampaignBrief(
    product="HydraSilk Shampoo",
    goal="Launch a campaign for colour-treated hair",
    audience="Adults aged 25 to 40",
    tone="Warm and confident",
    channels=["Instagram", "Email", "Search"],
    constraints=["No medical claims"],
)

RESEARCH = AudienceResearch(
    segments=[
        {
            "name": "Colour-treated professionals",
            "description": "Busy professionals who colour their hair monthly.",
        }
    ],
    pain_points=["Frizz after washing"],
    messaging_angles=["Repair without weighing hair down"],
    sources=[
        {
            "url": "https://example.com/research/hair-care-trends",
            "title": "Hair care trends: scalp-first routines",
        }
    ],
)

CURRENT_COPY: dict[str, Any] = {
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
        {
            "channel": "Search",
            "headline": "Colour care, simplified",
            "description": "Find a simple routine for colour-treated hair.",
            "cta": "Get started",
        },
    ]
}

REVISED_COPY: dict[str, Any] = {
    "variants": [
        CURRENT_COPY["variants"][0],
        {
            "channel": "Email",
            "headline": "Softer hair, no promises",
            "description": "A gentle weekly routine for colour-treated hair.",
            "cta": "See the routine",
        },
        CURRENT_COPY["variants"][2],
    ]
}

CHANGED_UNFLAGGED: dict[str, Any] = {
    "variants": [
        {
            **CURRENT_COPY["variants"][0],
            "headline": "Repair starts today",
        },
        CURRENT_COPY["variants"][1],
        CURRENT_COPY["variants"][2],
    ]
}

COMPLIANCE = ComplianceReport(
    items=[
        ComplianceItem(
            check="variant 2 (Email): guaranteed results",
            passed=False,
            reason="Guaranteed results are not allowed.",
        )
    ]
)

POLICY_MATCH = PolicyMatch(
    id=UUID("00000000-0000-0000-0000-000000000001"),
    title="Claims policy",
    source="policy://claims",
    content="Do not promise guaranteed results or before-and-after outcomes.",
    distance=0.1,
)
