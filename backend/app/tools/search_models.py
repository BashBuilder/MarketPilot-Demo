"""Typed search results and the provider protocol used by the Research agent."""

from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SearchResult(BaseModel):
    """One search hit; the source URL is mandatory so provenance is kept."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    source_url: HttpUrl
    title: Annotated[str, Field(min_length=1, max_length=300)]
    snippet: Annotated[str, Field(min_length=1, max_length=2000)]


class SearchArgs(BaseModel):
    """Validated arguments for the ``search_tools`` tool."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=2, max_length=500)]
    max_results: Annotated[int, Field(ge=1, le=10)] = 5


class SearchProvider(Protocol):
    """Backend that turns a query into attributed search results."""

    async def search(self, query: str, max_results: int) -> list[SearchResult]: ...
