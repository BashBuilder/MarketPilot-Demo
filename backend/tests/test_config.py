"""Tests for strict, fail-fast configuration loading."""

from pathlib import Path

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
    monkeypatch.delenv("ASSET_DIR", raising=False)
    monkeypatch.delenv("SEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("SCORE_THRESHOLD", raising=False)
    monkeypatch.delenv("MAX_AUTO_LOOPS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.deepseek_api_key.get_secret_value() == "test-key"
    assert settings.database_url.endswith("/marketpilot")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.asset_dir == Path("assets")
    assert settings.search_provider == "fake"
    assert settings.cost_cap_per_run == 3.5
    assert settings.image_provider == "fake"
    assert settings.max_image_calls_per_run == 8
    assert settings.max_search_calls_per_run == 20
    assert settings.retry_max_attempts == 3
    assert settings.score_threshold == 70
    assert settings.max_auto_loops == 2


def test_settings_reject_zero_retry_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "0")

    with pytest.raises(ValidationError, match="retry_max_attempts"):
        Settings(_env_file=None)


def test_settings_reject_negative_call_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("MAX_IMAGE_CALLS_PER_RUN", "-1")

    with pytest.raises(ValidationError, match="max_image_calls_per_run"):
        Settings(_env_file=None)


def test_settings_reject_non_positive_cost_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("COST_CAP_PER_RUN", "0")

    with pytest.raises(ValidationError, match="cost_cap_per_run"):
        Settings(_env_file=None)


def test_settings_reject_out_of_range_score_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SCORE_THRESHOLD", "101")

    with pytest.raises(ValidationError, match="score_threshold"):
        Settings(_env_file=None)


def test_settings_reject_negative_auto_loops(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("MAX_AUTO_LOOPS", "-1")

    with pytest.raises(ValidationError, match="max_auto_loops"):
        Settings(_env_file=None)
