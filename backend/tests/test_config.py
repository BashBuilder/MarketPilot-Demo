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
    monkeypatch.delenv("EVENT_STREAM_MAXLEN", raising=False)
    monkeypatch.delenv("EVENT_STREAM_TTL_SECONDS", raising=False)
    monkeypatch.delenv("RESUME_ON_STARTUP", raising=False)
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("IMAGE_API_URL", raising=False)
    monkeypatch.delenv("IMAGE_MODEL_ID", raising=False)
    monkeypatch.delenv("IMAGE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("SCORE_THRESHOLD", raising=False)
    monkeypatch.delenv("MAX_AUTO_LOOPS", raising=False)
    monkeypatch.delenv("MAX_IDEA_LENGTH", raising=False)
    monkeypatch.delenv("MAX_COMMENT_LENGTH", raising=False)
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    monkeypatch.delenv("MAX_CONCURRENT_RUNS", raising=False)
    monkeypatch.delenv("TRUST_PROXY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.deepseek_api_key.get_secret_value() == "test-key"
    assert settings.database_url.endswith("/marketpilot")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.event_stream_maxlen == 2000
    assert settings.event_stream_ttl_seconds == 86400
    assert settings.resume_on_startup is True
    assert settings.asset_dir == Path("assets")
    assert settings.search_provider == "fake"
    assert settings.cost_cap_per_run == 3.5
    assert settings.image_provider == "fake"
    assert settings.image_api_url is None
    assert settings.image_model_id == "stabilityai/sdxl-turbo"
    assert settings.image_timeout_seconds == 120.0
    assert settings.embedder == "fake"
    assert settings.hf_embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.max_image_calls_per_run == 8
    assert settings.max_generated_images_per_run == 2
    assert settings.max_search_calls_per_run == 20
    assert settings.retry_max_attempts == 3
    assert settings.score_threshold == 70
    assert settings.max_auto_loops == 2
    assert settings.max_idea_length == 2000
    assert settings.max_comment_length == 2000
    assert settings.rate_limit_per_minute == 20
    assert settings.max_concurrent_runs == 3
    assert settings.trust_proxy is False


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


def test_settings_accept_huggingface_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("EMBEDDER", "huggingface")

    settings = Settings(_env_file=None)

    assert settings.embedder == "huggingface"


def test_settings_reject_unknown_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("EMBEDDER", "remote")

    with pytest.raises(ValidationError, match="embedder"):
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


def test_settings_reject_zero_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")

    with pytest.raises(ValidationError, match="rate_limit_per_minute"):
        Settings(_env_file=None)


def test_settings_reject_zero_concurrent_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/marketpilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("MAX_CONCURRENT_RUNS", "0")

    with pytest.raises(ValidationError, match="max_concurrent_runs"):
        Settings(_env_file=None)
