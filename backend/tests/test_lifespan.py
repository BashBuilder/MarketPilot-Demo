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


def _configure(monkeypatch: pytest.MonkeyPatch, *, resume: str) -> None:
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("RESUME_ON_STARTUP", resume)

    async def no_seed() -> None:
        return None

    monkeypatch.setattr("app.main._seed_policies", no_seed)
    get_settings.cache_clear()


def test_startup_succeeds_with_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, resume="false")

    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_resumes_runs_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, resume="true")
    calls: list[dict[str, object]] = []

    async def fake_resume(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.main.resume_unfinished_runs", fake_resume)

    try:
        with TestClient(app):
            pass
    finally:
        get_settings.cache_clear()

    assert len(calls) == 1


def test_startup_skips_resume_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, resume="false")
    calls: list[dict[str, object]] = []

    async def fake_resume(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.main.resume_unfinished_runs", fake_resume)

    try:
        with TestClient(app):
            pass
    finally:
        get_settings.cache_clear()

    assert calls == []
