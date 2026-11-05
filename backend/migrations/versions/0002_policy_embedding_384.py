"""resize policy embeddings for the local model

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05

The selected HuggingFace sentence-transformers model returns 384 dimensions.
Policy vectors are derived data, so the column is recreated empty and startup
seeding re-embeds the sample policies with the active embedder.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the 1536-dimensional column with the 384-dimensional one."""
    op.drop_column("policy_documents", "embedding")
    op.add_column(
        "policy_documents",
        sa.Column("embedding", Vector(384), nullable=True),
    )


def downgrade() -> None:
    """Restore the original OpenAI-sized vector column."""
    op.drop_column("policy_documents", "embedding")
    op.add_column(
        "policy_documents",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
