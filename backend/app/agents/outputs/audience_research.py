"""Audience research produced by the Research agent."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from app.agents.outputs.base import OutputModel, TextList


class AudienceSegment(OutputModel):
    """One addressable audience segment."""

    name: Annotated[str, Field(min_length=2)]
    description: Annotated[str, Field(min_length=5)]


class AudienceResearch(OutputModel):
    """Evidence-backed segments, pain points and messaging angles."""

    segments: Annotated[list[AudienceSegment], Field(min_length=1)]
    pain_points: TextList
    messaging_angles: TextList

    @model_validator(mode="after")
    def _segment_names_unique(self) -> Self:
        names = [segment.name.casefold() for segment in self.segments]
        if len(names) != len(set(names)):
            raise ValueError("segment names must be unique")
        return self
