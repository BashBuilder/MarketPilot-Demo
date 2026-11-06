"""Weighted creative score produced by the Reviewer agent."""

from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from app.agents.outputs.base import OutputModel
from app.agents.scoring import DIMENSION_WEIGHTS, weighted_total

__all__ = ["DIMENSION_WEIGHTS", "CreativeScore", "ScoreDimension"]


class ScoreDimension(OutputModel):
    """A 0 to 10 score with the one-line reason behind it."""

    score: Annotated[float, Field(ge=0, le=10)]
    justification: Annotated[
        str,
        Field(
            min_length=5,
            max_length=200,
            description="One line, at most 200 characters.",
        ),
    ]

    @field_validator("justification")
    @classmethod
    def _single_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("justification must be a single line")
        return value


class CreativeScore(OutputModel):
    """Dimension scores plus the weighted total the Reviewer must match.

    ``compliance_risk`` is inverted: 10 means the lowest risk, so a safe
    package scores highly on every dimension.
    """

    brief_alignment: ScoreDimension
    audience_fit: ScoreDimension
    copy_quality: ScoreDimension
    visual_quality: ScoreDimension
    compliance_risk: ScoreDimension
    total: Annotated[float, Field(ge=0, le=100)]

    @model_validator(mode="after")
    def _total_matches_dimensions(self) -> Self:
        expected = weighted_total(
            {
                "brief_alignment": self.brief_alignment.score,
                "audience_fit": self.audience_fit.score,
                "copy_quality": self.copy_quality.score,
                "visual_quality": self.visual_quality.score,
                "compliance_risk": self.compliance_risk.score,
            }
        )
        if abs(self.total - expected) > 0.01:
            raise ValueError(f"total must equal the weighted dimensions ({expected})")
        return self
