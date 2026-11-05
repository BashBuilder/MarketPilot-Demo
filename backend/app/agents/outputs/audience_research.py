"""Audience research produced by the Research agent."""

from typing import Annotated, Self

from pydantic import Field, HttpUrl, model_validator

from app.agents.outputs.base import OutputModel, TextList


class AudienceSegment(OutputModel):
    """One addressable audience segment."""

    name: Annotated[str, Field(min_length=2)]
    description: Annotated[str, Field(min_length=5)]


class AudienceSource(OutputModel):
    """A source the Research agent actually retrieved and cited."""

    url: HttpUrl
    title: Annotated[str, Field(min_length=1, max_length=300)]


class AudienceResearch(OutputModel):
    """Evidence-backed segments, pain points, messaging angles and sources."""

    segments: Annotated[list[AudienceSegment], Field(min_length=1)]
    pain_points: TextList
    messaging_angles: TextList
    sources: Annotated[list[AudienceSource], Field(min_length=1)]

    @model_validator(mode="after")
    def _segment_names_unique(self) -> Self:
        names = [segment.name.casefold() for segment in self.segments]
        if len(names) != len(set(names)):
            raise ValueError("segment names must be unique")
        return self
