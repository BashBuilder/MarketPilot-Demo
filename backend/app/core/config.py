"""Validated runtime configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ImageProvider = Literal["fake", "flux", "sdxl"]


class Settings(BaseSettings):
    """Process configuration.

    Required fields raise a pydantic ``ValidationError`` naming each missing
    variable, so a misconfigured process fails at startup rather than mid-run.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    deepseek_api_key: SecretStr
    deepseek_base_url: str = "https://api.deepseek.com"
    database_url: str
    redis_url: str
    image_provider: ImageProvider = "fake"
    cost_cap_per_run: float = Field(default=2.0, gt=0)
    frontend_origin: str = "http://localhost:3000"
    log_level: LogLevel = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once per process so invalid config surfaces immediately."""
    # pydantic-settings fills required fields from the environment at runtime;
    # mypy cannot see that, so the synthesized constructor signature is too strict.
    return Settings()  # type: ignore[call-arg]
