"""Asset model: generated or edited media referenced by URI, never stored inline."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class AssetKind(StrEnum):
    """Kinds of media the Designer can produce."""

    IMAGE = "image"
    VIDEO = "video"


def _kind_values(enum_cls: type[StrEnum]) -> list[str]:
    """Persist enum values rather than member names for readable rows."""
    return [str(member.value) for member in enum_cls]


class Asset(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Generation metadata for a binary living on disk or object storage."""

    __tablename__ = "assets"

    campaign_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_versions.id"), nullable=False, index=True
    )
    kind: Mapped[AssetKind] = mapped_column(
        SqlEnum(
            AssetKind,
            native_enum=False,
            length=16,
            validate_strings=True,
            values_callable=_kind_values,
        ),
        nullable=False,
        default=AssetKind.IMAGE,
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    seed: Mapped[int | None] = mapped_column(BigInteger)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(64))
