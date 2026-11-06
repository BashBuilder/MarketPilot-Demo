"""Repository functions for the media attached to a campaign version.

Rows are written once, when a version snapshot is taken; versions and their
assets are append-only, so there is no update or delete helper.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Asset, AssetKind


@dataclass(frozen=True, slots=True)
class AssetRecord:
    """The generation metadata persisted for one asset."""

    uri: str
    checksum: str
    model: str
    seed: int | None
    prompt: str
    kind: AssetKind = AssetKind.IMAGE
    media_type: str | None = None


async def create_for_version(
    session: AsyncSession,
    *,
    campaign_version_id: UUID,
    assets: Sequence[AssetRecord],
) -> list[Asset]:
    """Persist one row per asset so the URI is queryable outside the package."""
    rows = [
        Asset(
            campaign_version_id=campaign_version_id,
            kind=record.kind,
            uri=record.uri,
            checksum=record.checksum,
            model=record.model,
            seed=record.seed,
            prompt=record.prompt,
            media_type=record.media_type,
        )
        for record in assets
    ]
    session.add_all(rows)
    await session.flush()
    return rows


async def list_for_version(session: AsyncSession, campaign_version_id: UUID) -> Sequence[Asset]:
    result = await session.scalars(
        select(Asset)
        .where(Asset.campaign_version_id == campaign_version_id)
        .order_by(Asset.created_at.asc())
    )
    return result.all()
