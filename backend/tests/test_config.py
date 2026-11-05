"""Tests for strict, fail-fast configuration loading."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

REQUIRED_ENV = ("DEEPSEEK_API_KEY", "DATABASE_URL", "REDIS_URL")


def test_missing_required_settings_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None)

    message = str(excinfo.value)
    for name in REQUIRED_ENV:
        assert name.lower() in message
    assert "Field required" in message


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("COST_CAP_PER_RUN", "3.5")

    settings = Settings(_env_file=None)

    assert settings.deepseek_api_key.get_secret_value() == "test-key"
    assert settings.database_url.endswith("/marketpilot")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.cost_cap_per_run == 3.5
    assert settings.image_provider == "fake"


def test_settings_reject_non_positive_cost_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("COST_CAP_PER_RUN", "0")

    with pytest.raises(ValidationError, match="cost_cap_per_run"):
        Settings(_env_file=None)
