"""Weighted creative score produced by the Reviewer agent."""

from typing import Annotated, Final, Self

from pydantic import Field, field_validator, model_validator

from app.agents.outputs.base import OutputModel

# Section 4 rubric: five equally weighted dimensions, total out of 100.
DIMENSION_WEIGHTS: Final[dict[str, float]] = {
    "brief_alignment": 0.2,
    "audience_fit": 0.2,
    "copy_quality": 0.2,
    "visual_quality": 0.2,
    "compliance_risk": 0.2,
}


class ScoreDimension(OutputModel):
    """A 0 to 10 score with the one-line reason behind it."""

    score: Annotated[float, Field(ge=0, le=10)]
    justification: Annotated[str, Field(min_length=5, max_length=200)]

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
        weighted = (
            self.brief_alignment.score * DIMENSION_WEIGHTS["brief_alignment"]
            + self.audience_fit.score * DIMENSION_WEIGHTS["audience_fit"]
            + self.copy_quality.score * DIMENSION_WEIGHTS["copy_quality"]
            + self.visual_quality.score * DIMENSION_WEIGHTS["visual_quality"]
            + self.compliance_risk.score * DIMENSION_WEIGHTS["compliance_risk"]
        )
        expected = round(weighted * 10, 2)
        if abs(self.total - expected) > 0.01:
            raise ValueError(f"total must equal the weighted dimensions ({expected})")
        return self
