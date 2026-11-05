"""Structured campaign brief produced by the Brief agent."""

from typing import Annotated

from pydantic import Field

from app.agents.outputs.base import OutputModel, TextList


class CampaignBrief(OutputModel):
    """The campaign request reframed as executable direction.

    Field lengths are deliberately loose: they reject empty or placeholder
    output without forcing the Brief agent into an artificial word count.
    """

    product: Annotated[str, Field(min_length=2)]
    goal: Annotated[str, Field(min_length=5)]
    audience: Annotated[str, Field(min_length=5)]
    tone: Annotated[str, Field(min_length=3)]
    channels: TextList
    constraints: TextList
