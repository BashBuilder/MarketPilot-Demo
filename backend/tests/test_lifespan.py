"""Tests that application startup enforces configuration before serving."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import app

REQUIRED_ENV = {
    "DEEPSEEK_API_KEY": "test-key",
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/marketpilot",
    "REDIS_URL": "redis://localhost:6379/0",
}


def test_startup_fails_fast_without_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    async def no_seed() -> None:
        return None

    monkeypatch.setattr("app.main._seed_policies", no_seed)
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(_env_file=None))

    with pytest.raises(ValidationError, match="deepseek_api_key"):
        with TestClient(app):
            pass

    get_settings.cache_clear()


def test_startup_succeeds_with_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()

    async def no_seed() -> None:
        return None

    monkeypatch.setattr("app.main._seed_policies", no_seed)

    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
