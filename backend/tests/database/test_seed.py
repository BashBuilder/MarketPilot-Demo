"""Tests that seeding demo data is idempotent."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import EMBEDDING_DIMENSIONS, Base, Campaign, PolicyDocument
from app.database.seed import SAMPLE_POLICY_DOCUMENTS, seed
from app.database.session import session_scope
from app.llm.embeddings import FakeEmbedder


class _NamedFakeEmbedder(FakeEmbedder):
    """Fake embedder whose identity changes without changing the vectors."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


@pytest.fixture()
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def test_seed_is_idempotent(engine: AsyncEngine) -> None:
    async with session_scope(engine) as session:
        await seed(session)

    async with session_scope(engine) as session:
        documents = (await session.scalars(select(PolicyDocument))).all()
        first_embeddings = {document.title: document.embedding for document in documents}

    async with session_scope(engine) as session:
        await seed(session)

    async with session_scope(engine) as session:
        campaign_count = await session.scalar(select(func.count()).select_from(Campaign))
        documents = (await session.scalars(select(PolicyDocument))).all()

    assert campaign_count == 1
    assert {document.title for document in documents} == {
        title for title, _, _ in SAMPLE_POLICY_DOCUMENTS
    }
    assert len(documents) == len(SAMPLE_POLICY_DOCUMENTS)
    for document in documents:
        assert document.embedding is not None
        assert len(document.embedding) == EMBEDDING_DIMENSIONS
        assert document.embedding == first_embeddings[document.title]
        assert document.doc_metadata["embedder"] == "fake"


async def test_seed_reembeds_when_the_embedder_changes(engine: AsyncEngine) -> None:
    async with session_scope(engine) as session:
        await seed(session, embedder=_NamedFakeEmbedder("first"))

    async with session_scope(engine) as session:
        await seed(session, embedder=_NamedFakeEmbedder("second"))

    async with session_scope(engine) as session:
        documents = (await session.scalars(select(PolicyDocument))).all()

    assert len(documents) == len(SAMPLE_POLICY_DOCUMENTS)
    for document in documents:
        assert document.embedding is not None
        assert document.doc_metadata["embedder"] == "second"
