"""Validated runtime configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ImageProvider = Literal["fake", "hosted", "huggingface"]
SearchProviderName = Literal["fake"]
EmbedderName = Literal["fake", "huggingface"]
AssetStorageName = Literal["local", "cloudinary"]


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
    event_stream_maxlen: int = Field(default=2000, ge=1)
    event_stream_ttl_seconds: int = Field(default=86400, ge=1)
    resume_on_startup: bool = True
    image_provider: ImageProvider = "fake"
    image_api_url: str | None = None
    image_api_key: SecretStr | None = None
    image_model_id: str = Field(default="stabilityai/sdxl-turbo", min_length=1)
    image_timeout_seconds: float = Field(default=45.0, gt=0)
    search_provider: SearchProviderName = "fake"
    embedder: EmbedderName = "fake"
    hf_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", min_length=1)
    huggingfacehub_api_token: SecretStr | None = None
    asset_dir: Path = Path("assets")
    asset_storage: AssetStorageName = "local"
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: SecretStr | None = None
    cloudinary_api_secret: SecretStr | None = None
    cloudinary_folder: str = Field(default="marketpilot", min_length=1)
    cloudinary_timeout_seconds: float = Field(default=30.0, gt=0)
    cost_cap_per_run: float = Field(default=2.0, gt=0)
    max_image_calls_per_run: int = Field(default=8, ge=0)
    max_generated_images_per_run: int = Field(default=1, ge=1)
    max_search_calls_per_run: int = Field(default=20, ge=0)
    max_image_prompt_length: int = Field(default=1000, ge=1)
    retry_max_attempts: int = Field(default=3, ge=1)
    score_threshold: int = Field(default=70, ge=0, le=100)
    max_auto_loops: int = Field(default=2, ge=0)
    max_idea_length: int = Field(default=2000, ge=1)
    max_comment_length: int = Field(default=2000, ge=1)
    rate_limit_per_minute: int = Field(default=20, ge=1)
    max_concurrent_runs: int = Field(default=3, ge=1)
    trust_proxy: bool = False
    frontend_origin: str = "http://localhost:3000"
    log_level: LogLevel = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once per process so invalid config surfaces immediately."""
    # pydantic-settings fills required fields from the environment at runtime;
    # mypy cannot see that, so the synthesized constructor signature is too strict.
    return Settings()  # type: ignore[call-arg]
