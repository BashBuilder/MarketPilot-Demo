"""Idempotent demo data: one campaign and the sample policy documents."""

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Campaign, CampaignStatus, PolicyDocument
from app.database.session import session_scope
from app.llm.embeddings import Embedder, get_embedder

DEMO_CAMPAIGN_ID = UUID("00000000-0000-4000-8000-000000000001")
DEMO_CAMPAIGN_IDEA = (
    "Create an advertising campaign for a fictional hair-care product "
    "targeting adults aged 25 to 40"
)

# (title, source, content) — embeddings are computed with the active embedder.
SAMPLE_POLICY_DOCUMENTS: tuple[tuple[str, str, str], ...] = (
    (
        "Medical claims",
        "policy://medical-claims",
        "Do not make unapproved medical, therapeutic or curative claims. "
        "Only claims supported by substantiation may appear in ad copy.",
    ),
    (
        "Guaranteed results",
        "policy://guaranteed-results",
        "Do not promise guaranteed outcomes, instant results or risk-free "
        "performance. Avoid absolute language such as 'cures' or 'always works'.",
    ),
    (
        "Minors and likeness",
        "policy://minors-and-likeness",
        "Do not target minors or use real people's likeness without consent. "
        "Do not reference copyrighted characters or third-party brands.",
    ),
)


async def seed(session: AsyncSession, embedder: Embedder | None = None) -> None:
    """Insert missing demo rows and backfill missing embeddings; idempotent."""
    active_embedder = embedder if embedder is not None else get_embedder()
    if await session.get(Campaign, DEMO_CAMPAIGN_ID) is None:
        session.add(
            Campaign(
                id=DEMO_CAMPAIGN_ID,
                idea=DEMO_CAMPAIGN_IDEA,
                status=CampaignStatus.DRAFT,
            )
        )

    existing = {
        document.title: document
        for document in (await session.scalars(select(PolicyDocument))).all()
    }
    pending = [
        (title, source, content)
        for title, source, content in SAMPLE_POLICY_DOCUMENTS
        if title not in existing or existing[title].embedding is None
    ]
    if pending:
        vectors = await active_embedder.embed([content for _, _, content in pending])
        for (title, source, content), vector in zip(pending, vectors, strict=True):
            document = existing.get(title)
            if document is None:
                session.add(
                    PolicyDocument(
                        title=title,
                        source=source,
                        content=content,
                        doc_metadata={"category": "advertising", "version": "1.0"},
                        embedding=vector,
                    )
                )
            else:
                document.embedding = vector

    await session.flush()


async def main() -> None:
    async with session_scope() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
