"""Shared fixtures for graph state tests."""

import pytest

from app.agents.outputs import (
    AdCopySet,
    AssetSet,
    AudienceResearch,
    CampaignBrief,
    ComplianceReport,
    CreativeDirection,
    CreativeScore,
)
from app.graph.state import WorkflowState


def _dimension(score: float) -> dict[str, object]:
    return {"score": score, "justification": "Clear rationale."}


@pytest.fixture
def full_state() -> WorkflowState:
    return WorkflowState(
        idea="Create an advertising campaign for a fictional hair-care product",
        brief=CampaignBrief(
            product="Aurelia Repair Shampoo",
            goal="Launch a repair line for adults",
            audience="Adults aged 25 to 40",
            tone="Warm and confident",
            channels=["Instagram"],
            constraints=["No medical claims"],
        ),
        research=AudienceResearch(
            segments=[{"name": "Professionals", "description": "Busy professionals."}],
            pain_points=["Frizz"],
            messaging_angles=["Repair without weight"],
        ),
        copy=AdCopySet(
            variants=[
                {
                    "channel": "Instagram",
                    "headline": "Repair starts here",
                    "description": "A weekly ritual for colour-treated hair.",
                    "cta": "Shop now",
                }
            ]
        ),
        direction=CreativeDirection(
            image_prompts=["Soft-lit studio portrait"],
            video_prompts=["Slow dolly shot"],
            style_guide="Warm neutrals and editorial calm",
            composition="Rule of thirds with open space",
            negative_prompts=["watermark"],
        ),
        assets=AssetSet(
            assets=[
                {
                    "uri": "s3://bucket/hero.png",
                    "checksum": "a" * 64,
                    "model": "flux",
                    "seed": 1,
                    "prompt": "Editorial portrait",
                }
            ]
        ),
        compliance=ComplianceReport(
            items=[
                {
                    "check": "Medical claims",
                    "passed": True,
                    "reason": "No claims found.",
                }
            ]
        ),
        score=CreativeScore(
            brief_alignment=_dimension(8),
            audience_fit=_dimension(7),
            copy_quality=_dimension(9),
            visual_quality=_dimension(8),
            compliance_risk=_dimension(6),
            total=76.0,
        ),
        versions=[1, 2],
        status="awaiting_approval",
        retry_counters={"research": 1},
        errors=["copy retried once"],
    )
