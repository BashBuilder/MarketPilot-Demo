"""Declarative base and shared column mixins.

The naming convention keeps every constraint and index name deterministic, so
Alembic autogenerate produces stable diffs instead of anonymous names.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData, Uuid, event, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Give a model a client-generated UUID primary key."""

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


class CreatedAtMixin:
    """Marks a row as immutable once written: creation time only, no updated_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TimestampMixin(CreatedAtMixin):
    """Adds a server-maintained updated_at for rows that change after insert."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImmutableRowError(RuntimeError):
    """Raised when an append-only row is updated or deleted."""


def guard_immutable(model: type[Base], error: type[RuntimeError] = ImmutableRowError) -> None:
    """Reject ORM updates and deletes for an append-only table.

    Mapper events only cover unit-of-work flushes; bulk ``UPDATE``/``DELETE``
    bypasses them, so migrations add a database trigger for the final guarantee.
    """

    @event.listens_for(model, "before_update")
    @event.listens_for(model, "before_delete")
    def _reject(*_args: object) -> None:
        raise error(f"{model.__tablename__} rows are append-only")
