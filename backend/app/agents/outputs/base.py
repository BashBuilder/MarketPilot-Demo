"""Shared configuration and validators for agent output models."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class OutputModel(BaseModel):
    """Base for validated, immutable agent outputs.

    ``extra="forbid"`` rejects keys the agent was not asked to produce, so a
    drifted prompt cannot smuggle data into workflow state. ``frozen=True``
    keeps a validated output from being mutated after the node wrapper merges
    it.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


def _non_blank_unique(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = item.strip()
        if not value:
            raise ValueError("list items must not be blank")
        key = value.casefold()
        if key in seen:
            raise ValueError(f"duplicate list item: {value!r}")
        seen.add(key)
        cleaned.append(value)
    return cleaned


Text = Annotated[str, Field(min_length=1)]
TextList = Annotated[list[Text], Field(min_length=1), AfterValidator(_non_blank_unique)]
