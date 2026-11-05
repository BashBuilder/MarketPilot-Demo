"""Policy lookup against real Postgres: ranking, read-only behaviour, permissions."""

from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.errors import GuardrailViolation
from app.database.models import PolicyDocument
from app.database.seed import SAMPLE_POLICY_DOCUMENTS, seed
from app.database.session import get_sessionmaker, session_scope
from app.harness.registry import ToolRegistry
from app.llm.embeddings import FakeEmbedder
from app.tools.policy_models import PolicyLookupArgs
from app.tools.policy_tools import POLICY_TOOL_NAME, policy_lookup, register_policy_tools

pytestmark = pytest.mark.postgres


@pytest.fixture()
async def offline_registry() -> AsyncIterator[ToolRegistry]:
    engine = create_async_engine("sqlite+aiosqlite://")
    registry = ToolRegistry()
    register_policy_tools(
        registry,
        session_factory=get_sessionmaker(engine),
        embedder=FakeEmbedder(),
    )
    yield registry
    await engine.dispose()


@pytest.fixture()
async def seeded_engine(pg_engine: AsyncEngine) -> AsyncEngine:
    async with session_scope(pg_engine) as session:
        await seed(session, embedder=FakeEmbedder())
    return pg_engine


async def test_closest_seeded_policy_is_returned(seeded_engine: AsyncEngine) -> None:
    registry = ToolRegistry()
    register_policy_tools(
        registry,
        session_factory=get_sessionmaker(seeded_engine),
        embedder=FakeEmbedder(),
    )
    target_title, _, target_content = SAMPLE_POLICY_DOCUMENTS[0]

    matches = await registry.get_tool("compliance", POLICY_TOOL_NAME).run(
        PolicyLookupArgs(query=target_content, top_k=1)
    )

    assert len(matches) == 1
    assert matches[0].title == target_title
    assert matches[0].distance == pytest.approx(0.0, abs=1e-5)


async def test_lookup_is_read_only(seeded_engine: AsyncEngine) -> None:
    session_factory = get_sessionmaker(seeded_engine)
    async with session_scope(seeded_engine) as session:
        before = (await session.scalars(select(PolicyDocument))).all()

    statements: list[str] = []

    def capture(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        statements.append(statement)

    event.listen(seeded_engine.sync_engine, "before_cursor_execute", capture)
    try:
        matches = await policy_lookup(
            PolicyLookupArgs(query=SAMPLE_POLICY_DOCUMENTS[1][2], top_k=3),
            session_factory=session_factory,
            embedder=FakeEmbedder(),
        )
    finally:
        event.remove(seeded_engine.sync_engine, "before_cursor_execute", capture)

    assert matches
    assert statements
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)

    async with session_scope(seeded_engine) as session:
        after = (await session.scalars(select(PolicyDocument))).all()

    assert {document.id for document in after} == {document.id for document in before}
    assert {document.id: document.updated_at for document in after} == {
        document.id: document.updated_at for document in before
    }
    assert all(document.embedding is not None for document in after)


@pytest.mark.parametrize("agent", ["copywriter", "compliance", "reviewer"])
async def test_allowed_agents_can_resolve_the_tool(
    offline_registry: ToolRegistry, agent: str
) -> None:
    assert offline_registry.get_tool(agent, POLICY_TOOL_NAME).name == POLICY_TOOL_NAME  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "agent",
    ["brief", "research", "creative_director", "designer", "supervisor"],
)
async def test_other_agents_are_denied(offline_registry: ToolRegistry, agent: str) -> None:
    with pytest.raises(GuardrailViolation, match="may not use"):
        offline_registry.get_tool(agent, POLICY_TOOL_NAME)  # type: ignore[arg-type]


def test_args_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        PolicyLookupArgs(query="")
    with pytest.raises(ValidationError):
        PolicyLookupArgs(query="medical claims", top_k=0)
