"""Visual direction produced by the Creative Director agent."""

from typing import Annotated

from pydantic import Field

from app.agents.outputs.base import OutputModel, TextList


class CreativeDirection(OutputModel):
    """Prompts and constraints the Designer turns into asset requests."""

    image_prompts: TextList
    video_prompts: TextList
    style_guide: Annotated[str, Field(min_length=5)]
    composition: Annotated[str, Field(min_length=5)]
    negative_prompts: TextList
