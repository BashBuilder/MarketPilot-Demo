"""Async engine ownership and per-request/run session lifecycle.

The engine (and its connection pool) is shared; sessions never are. Callers get a
session through ``session_scope`` or the app-owned session factory, and every
session is closed by its context manager.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide engine, creating its pool on first use."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to the shared engine or an explicit one."""
    return async_sessionmaker(engine or get_engine(), expire_on_commit=False)


@asynccontextmanager
async def session_scope(engine: AsyncEngine | None = None) -> AsyncIterator[AsyncSession]:
    """Open one session, commit on success, roll back on any exception."""
    async with get_sessionmaker(engine)() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Release pooled connections during app shutdown or test teardown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
