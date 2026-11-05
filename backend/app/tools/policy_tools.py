"""Read-only pgvector policy lookup used by Copywriter, Compliance and Reviewer."""

from functools import partial

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ToolError
from app.database.models import PolicyDocument
from app.harness.registry import ToolRegistry, ToolSpec
from app.llm.embeddings import Embedder
from app.tools.policy_models import PolicyLookupArgs, PolicyMatch

POLICY_TOOL_NAME = "policy_lookup"


async def policy_lookup(
    args: PolicyLookupArgs,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    embedder: Embedder,
) -> list[PolicyMatch]:
    """Return the closest policies without writing to the database."""
    vectors = await embedder.embed([args.query])
    if not vectors:
        raise ToolError("embedder returned no vector for the policy query")

    distance = PolicyDocument.embedding.cosine_distance(vectors[0]).label("distance")
    statement = (
        select(
            PolicyDocument.id,
            PolicyDocument.title,
            PolicyDocument.source,
            PolicyDocument.content,
            distance,
        )
        .where(PolicyDocument.embedding.is_not(None))
        .order_by(distance)
        .limit(args.top_k)
    )

    async with session_factory() as session:
        rows = (await session.execute(statement)).all()

    return [
        PolicyMatch(
            id=row.id,
            title=row.title,
            source=row.source,
            content=row.content,
            distance=float(row.distance),
        )
        for row in rows
    ]


def register_policy_tools(
    registry: ToolRegistry,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    embedder: Embedder,
) -> None:
    """Register the lookup; the allowlist still limits it to three agents."""
    registry.register_tool(
        ToolSpec(
            name=POLICY_TOOL_NAME,
            args_model=PolicyLookupArgs,
            run=partial(policy_lookup, session_factory=session_factory, embedder=embedder),
        )
    )
