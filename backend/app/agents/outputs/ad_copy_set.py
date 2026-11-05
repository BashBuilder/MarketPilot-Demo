"""Advertising copy produced by the Copywriter agent."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from app.agents.outputs.base import OutputModel


class CopyVariant(OutputModel):
    """A headline, description and call to action for one channel."""

    channel: Annotated[str, Field(min_length=2)]
    headline: Annotated[str, Field(min_length=5)]
    description: Annotated[str, Field(min_length=10)]
    cta: Annotated[str, Field(min_length=2)]


class AdCopySet(OutputModel):
    """Copy variants grouped by channel.

    Requiring several variants per channel is a pipeline completeness rule,
    so the schema only rejects empty output and duplicate variants.
    """

    variants: Annotated[list[CopyVariant], Field(min_length=1)]

    @model_validator(mode="after")
    def _variants_unique(self) -> Self:
        keys = [
            (variant.channel.casefold(), variant.headline.casefold()) for variant in self.variants
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate variant for the same channel and headline")
        return self
