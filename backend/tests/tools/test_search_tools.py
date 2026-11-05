"""Search tool: provenance, per-run cap and Research-only permissions."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import GuardrailViolation
from app.harness.guardrails import RunGuardrails
from app.harness.registry import ToolRegistry
from app.tools.search_models import SearchArgs, SearchResult
from app.tools.search_tools import (
    SEARCH_TOOL_NAME,
    FakeSearchProvider,
    register_search_tools,
    search_tools,
)


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        deepseek_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/marketpilot",
        redis_url="redis://localhost:6379/0",
        **overrides,
    )


def registry_with(provider: FakeSearchProvider) -> ToolRegistry:
    registry = ToolRegistry()
    register_search_tools(registry, provider)
    return registry


async def call_search(
    registry: ToolRegistry,
    guardrails: RunGuardrails,
    payload: dict[str, object],
) -> list[SearchResult]:
    """Mirror the middleware order: allowlist, budget, validate, run."""
    spec = registry.get_tool("research", SEARCH_TOOL_NAME)
    guardrails.record_call(SEARCH_TOOL_NAME)
    args = spec.args_model.model_validate(payload)
    result = await spec.run(args)
    return result


async def test_fake_results_keep_provenance() -> None:
    results = await search_tools(
        SearchArgs(query="hair care audience"),
        provider=FakeSearchProvider(),
    )

    assert len(results) == 3
    for result in results:
        assert str(result.source_url).startswith("https://")
        assert result.title
        assert result.snippet


async def test_results_are_truncated_to_the_requested_count() -> None:
    provider = FakeSearchProvider()

    assert len(await provider.search("hair care audience", 1)) == 1
    assert len(await provider.search("hair care audience", 10)) == 3


async def test_search_cap_is_enforced_per_run() -> None:
    registry = registry_with(FakeSearchProvider())
    guardrails = RunGuardrails(settings(max_search_calls_per_run=1))

    first = await call_search(registry, guardrails, {"query": "hair care audience"})
    assert first

    with pytest.raises(GuardrailViolation, match="search cap of 1"):
        await call_search(registry, guardrails, {"query": "hair care audience"})


def test_research_can_resolve_the_search_tool() -> None:
    spec = registry_with(FakeSearchProvider()).get_tool("research", SEARCH_TOOL_NAME)

    assert spec.name == SEARCH_TOOL_NAME


@pytest.mark.parametrize(
    "agent",
    [
        "brief",
        "copywriter",
        "creative_director",
        "designer",
        "compliance",
        "reviewer",
        "supervisor",
    ],
)
def test_other_agents_are_denied(agent: str) -> None:
    registry = registry_with(FakeSearchProvider())

    with pytest.raises(GuardrailViolation, match="may not use"):
        registry.get_tool(agent, SEARCH_TOOL_NAME)  # type: ignore[arg-type]


def test_args_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        SearchArgs(query="")
    with pytest.raises(ValidationError):
        SearchArgs(query="hair care audience", max_results=0)
