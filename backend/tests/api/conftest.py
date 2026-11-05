"""Shared fixtures for API tests."""

from collections.abc import AsyncIterator, Iterator
from dataclasses import replace

import pytest
from api_support import FRONTEND_ORIGIN, MAX_IDEA_LENGTH
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import (
    DEFAULT_WORKFLOW_SERVICES,
    RecordingRunLauncher,
    get_run_launcher,
    get_session,
)
from app.core.config import get_settings
from app.database.models import Base
from app.events.bus import InMemoryEventBus
from app.events.emitter import make_emitter
from app.main import app


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("FRONTEND_ORIGIN", FRONTEND_ORIGIN)
    monkeypatch.setenv("MAX_IDEA_LENGTH", str(MAX_IDEA_LENGTH))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def event_bus() -> Iterator[InMemoryEventBus]:
    """Install a fresh bus so API tests never touch the lifespan Redis client."""
    bus = InMemoryEventBus()
    previous_bus = app.state.event_bus
    previous_services = app.state.workflow_services
    app.state.event_bus = bus
    app.state.workflow_services = replace(
        DEFAULT_WORKFLOW_SERVICES,
        emit=make_emitter(bus),
    )
    yield bus
    app.state.event_bus = previous_bus
    app.state.workflow_services = previous_services


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture()
def launcher() -> RecordingRunLauncher:
    return RecordingRunLauncher()


@pytest.fixture()
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: RecordingRunLauncher,
) -> AsyncIterator[AsyncClient]:
    async def _session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_run_launcher] = lambda: launcher
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()
