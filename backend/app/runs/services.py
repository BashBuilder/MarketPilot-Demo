"""Production wiring for the workflow's agents, tools and run budgets.

Agents are stateless, so one mapping is shared by every run. Tool middleware is
run-scoped because its guardrails count calls and spend per run.
"""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.brief import BriefAgent
from app.agents.compliance import ComplianceAgent
from app.agents.copywriter import CopywriterAgent
from app.agents.creative_director import CreativeDirectorAgent
from app.agents.designer import DesignerAgent
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.core.config import Settings
from app.graph.nodes import NodeAgent
from app.graph.routing import PIPELINE
from app.harness.guardrails import RunGuardrails
from app.harness.middleware import ToolCallMiddleware
from app.harness.registry import AgentName, ToolRegistry
from app.llm.embeddings import get_embedder
from app.tools.image_providers import build_image_generator
from app.tools.image_tools import register_image_tools
from app.tools.policy_tools import register_policy_tools
from app.tools.search_tools import FakeSearchProvider, register_search_tools


def build_agents() -> dict[AgentName, NodeAgent]:
    """Return the seven pipeline agents; the Supervisor lives in graph routing."""
    return {
        "brief": BriefAgent(),
        "research": ResearchAgent(),
        "copywriter": CopywriterAgent(),
        "creative_director": CreativeDirectorAgent(),
        "designer": DesignerAgent(),
        "compliance": ComplianceAgent(),
        "reviewer": ReviewerAgent(),
    }


def build_tool_registry(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> ToolRegistry:
    """Register the tools the pipeline may use; the allowlist still applies."""
    registry = ToolRegistry()
    register_search_tools(registry, FakeSearchProvider())
    register_image_tools(registry, build_image_generator(settings))
    register_policy_tools(
        registry,
        session_factory=session_factory,
        embedder=get_embedder(),
    )
    return registry


def build_tools(
    *,
    registry: ToolRegistry,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
) -> Mapping[AgentName, ToolCallMiddleware]:
    """Bind one budget and audit middleware to each agent for a single run."""
    guardrails = RunGuardrails(settings)
    return {
        name: ToolCallMiddleware(
            registry=registry,
            guardrails=guardrails,
            session_factory=session_factory,
            run_id=run_id,
            agent=name,
        )
        for name in PIPELINE
    }
