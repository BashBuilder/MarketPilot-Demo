"""Validated runtime configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ImageProvider = Literal["fake", "flux", "sdxl"]
SearchProviderName = Literal["fake"]
EmbedderName = Literal["fake", "local"]


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
    search_provider: SearchProviderName = "fake"
    embedder: EmbedderName = "fake"
    asset_dir: Path = Path("assets")
    cost_cap_per_run: float = Field(default=2.0, gt=0)
    max_image_calls_per_run: int = Field(default=8, ge=0)
    max_search_calls_per_run: int = Field(default=20, ge=0)
    max_image_prompt_length: int = Field(default=1000, ge=1)
    retry_max_attempts: int = Field(default=3, ge=1)
    score_threshold: int = Field(default=70, ge=0, le=100)
    max_auto_loops: int = Field(default=2, ge=0)
    max_idea_length: int = Field(default=2000, ge=1)
    frontend_origin: str = "http://localhost:3000"
    log_level: LogLevel = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once per process so invalid config surfaces immediately."""
    # pydantic-settings fills required fields from the environment at runtime;
    # mypy cannot see that, so the synthesized constructor signature is too strict.
    return Settings()  # type: ignore[call-arg]
