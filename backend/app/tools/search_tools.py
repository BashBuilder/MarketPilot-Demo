"""Search tool with a deterministic fake provider.

Search results always carry their source URL so the Research agent can cite
only what it actually retrieved. A real provider can be added later behind the
same ``SearchProvider`` protocol.
"""

from functools import partial

from pydantic import HttpUrl

from app.harness.registry import ToolRegistry, ToolSpec
from app.tools.search_models import SearchArgs, SearchProvider, SearchResult

SEARCH_TOOL_NAME = "search_tools"

_FIXED_RESULTS: tuple[SearchResult, ...] = (
    SearchResult(
        source_url=HttpUrl("https://example.com/research/hair-care-trends"),
        title="Hair care trends: scalp-first routines",
        snippet=(
            "Adults aged 25 to 40 are moving toward scalp health, gentle "
            "cleansers and ingredient transparency."
        ),
    ),
    SearchResult(
        source_url=HttpUrl("https://example.com/research/audience-messaging"),
        title="Audience messaging for everyday personal care",
        snippet=(
            "Practical, low-hype language performs better than clinical claims for this audience."
        ),
    ),
    SearchResult(
        source_url=HttpUrl("https://example.com/research/ad-claims-guidance"),
        title="Advertising claims guidance for personal care",
        snippet=(
            "Avoid guaranteed outcomes and unapproved medical claims; support "
            "product benefits with evidence."
        ),
    ),
)


class FakeSearchProvider:
    """Returns fixed results, truncated to the requested count."""

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        return list(_FIXED_RESULTS[:max_results])


async def search_tools(
    args: SearchArgs,
    *,
    provider: SearchProvider,
) -> list[SearchResult]:
    return await provider.search(query=args.query, max_results=args.max_results)


def register_search_tools(registry: ToolRegistry, provider: SearchProvider) -> None:
    """Register the search tool; the allowlist still limits it to Research."""
    registry.register_tool(
        ToolSpec(
            name=SEARCH_TOOL_NAME,
            args_model=SearchArgs,
            run=partial(search_tools, provider=provider),
        )
    )
