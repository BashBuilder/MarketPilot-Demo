"""Per-agent state slicing and token budgeting.

Old research detail goes first, then long free text; the idea, brief and
compliance findings are never trimmed.
"""

from collections.abc import Callable, Mapping
from types import MappingProxyType

from pydantic import BaseModel

from app.agents.outputs import AudienceResearch
from app.core.errors import ContextBudgetExceeded
from app.graph.state import WorkflowState
from app.harness.registry import AgentName

type TokenEstimator = Callable[[str], int]

_CHARS_PER_TOKEN = 4
_MIN_SHRINK_LIMIT = 16
_PACKAGE_FIELDS = frozenset(
    {"brief", "research", "copy", "direction", "assets", "compliance", "score"}
)
_ROUTING_FIELDS = frozenset({"status", "retry_counters", "errors"})

# ``idea`` is added to every slice: no agent can act without the user's request.
AGENT_CONTEXT_FIELDS: Mapping[AgentName, frozenset[str]] = MappingProxyType(
    {
        "brief": frozenset(),
        "research": frozenset({"brief"}),
        "copywriter": frozenset({"brief", "research"}),
        "creative_director": frozenset({"brief", "research", "copy"}),
        "designer": frozenset({"direction"}),
        "compliance": frozenset({"brief", "copy"}),
        "reviewer": _PACKAGE_FIELDS,
        "supervisor": _PACKAGE_FIELDS | _ROUTING_FIELDS,
    }
)


def estimate_tokens(text: str) -> int:
    """Approximate tokens from characters; the estimator is swappable."""
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def estimate_context_tokens(
    state: WorkflowState, *, estimate: TokenEstimator = estimate_tokens
) -> int:
    return estimate(state.model_dump_json())


def build_agent_context(
    state: WorkflowState,
    agent_name: AgentName,
    budget: int,
    *,
    estimate: TokenEstimator = estimate_tokens,
) -> WorkflowState:
    """Return the fields ``agent_name`` needs, trimmed to ``budget`` tokens."""
    if budget < 1:
        raise ValueError("budget must be at least 1 token")
    context = _subset(state, agent_name)
    if _within(context, budget, estimate):
        return context
    context = _trim_research(context, budget, estimate)
    if _within(context, budget, estimate):
        return context
    context = _trim_free_text(context, budget, estimate)
    if _within(context, budget, estimate):
        return context
    raise ContextBudgetExceeded(
        f"context for {agent_name!r} exceeds the {budget} token budget",
        details={
            "agent": agent_name,
            "budget": budget,
            "tokens": estimate_context_tokens(context, estimate=estimate),
        },
    )


def _subset(state: WorkflowState, agent_name: AgentName) -> WorkflowState:
    data = state.model_dump()
    fields = ("idea", *AGENT_CONTEXT_FIELDS[agent_name])
    return WorkflowState.model_validate({name: data[name] for name in fields})


def _within(context: WorkflowState, budget: int, estimate: TokenEstimator) -> bool:
    return estimate_context_tokens(context, estimate=estimate) <= budget


def _trim_research(context: WorkflowState, budget: int, estimate: TokenEstimator) -> WorkflowState:
    """Drop the oldest research entries first; the newest evidence survives."""
    research = context.research
    if research is None:
        return context
    data = research.model_dump()
    for key in ("segments", "pain_points", "messaging_angles"):
        while len(data[key]) > 1 and not _within(context, budget, estimate):
            data[key] = data[key][1:]
            updated = AudienceResearch.model_validate(data)
            context = context.model_copy(update={"research": updated})
    return context


def _trim_free_text(context: WorkflowState, budget: int, estimate: TokenEstimator) -> WorkflowState:
    limit = 160
    while not _within(context, budget, estimate) and limit >= _MIN_SHRINK_LIMIT:
        context = _shrink_sections(context, limit)
        limit //= 2
    return context


_SHRINK_SKIP = frozenset({"channel", "name", "headline", "uri", "checksum", "model", "seed", "url"})


def _shrink_sections(context: WorkflowState, limit: int) -> WorkflowState:
    updates: dict[str, object] = {}
    for field in ("research", "copy", "direction", "assets"):
        section = getattr(context, field)
        if section is not None:
            updates[field] = _shrink_model(section, limit)
    return context.model_copy(update=updates) if updates else context


def _shrink_model[M: BaseModel](model: M, limit: int) -> M:
    data = _shrink_value(model.model_dump(), limit)
    return type(model).model_validate(data)


def _shrink_value(value: object, limit: int, *, key: str = "") -> object:
    if key in _SHRINK_SKIP:
        return value
    if isinstance(value, str):
        return value if len(value) <= limit else f"{value[:limit].rstrip()}..."
    if isinstance(value, list):
        items = [_shrink_value(item, limit) for item in value]
        if all(isinstance(item, str) for item in items):
            return list(dict.fromkeys(items))
        return items
    if isinstance(value, dict):
        return {k: _shrink_value(v, limit, key=k) for k, v in value.items()}
    return value
