"""Policy document model: reference text plus its pgvector embedding."""

from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Must match the selected local model. Changing it requires a migration that
# rewrites the pgvector column and a startup re-embed of seeded policies.
EMBEDDING_DIMENSIONS = 384

PolicyMetadata = dict[str, Any]


class PolicyDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A retrievable policy chunk; embedding is nullable until ingestion computes it."""

    __tablename__ = "policy_documents"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_metadata: Mapped[PolicyMetadata] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )
    # SQLite gets a JSON variant so model tests run without Postgres; production
    # always compiles to vector(1536).
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS).with_variant(JSON(), "sqlite")
    )
