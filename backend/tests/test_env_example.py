"""The example env file must document every setting a deployment can set."""

from pathlib import Path

from app.core.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"

PRODUCTION_VARS = (
    "DEEPSEEK_API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "FRONTEND_ORIGIN",
    "ASSET_STORAGE",
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
    "TRUST_PROXY",
)


def documented_names() -> set[str]:
    names: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        names.add(stripped.split("=", 1)[0].strip())
    return names


def test_env_example_documents_every_setting() -> None:
    missing = sorted(
        field.upper() for field in Settings.model_fields if field.upper() not in documented_names()
    )

    assert missing == []


def test_env_example_documents_production_variables() -> None:
    assert set(PRODUCTION_VARS) <= documented_names()
