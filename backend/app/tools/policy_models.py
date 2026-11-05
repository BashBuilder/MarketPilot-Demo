"""Typed arguments and results for the policy lookup tool."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PolicyLookupArgs(BaseModel):
    """Validated arguments for ``policy_lookup``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=2, max_length=500)]
    top_k: Annotated[int, Field(ge=1, le=10)] = 3


class PolicyMatch(BaseModel):
    """One policy hit with its cosine distance to the query."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: UUID
    title: Annotated[str, Field(min_length=1)]
    source: str | None = None
    content: Annotated[str, Field(min_length=1)]
    distance: Annotated[float, Field(ge=0)]
