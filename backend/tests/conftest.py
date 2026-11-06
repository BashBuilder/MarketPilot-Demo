"""Shared test defaults that must not depend on a developer's local ``.env``."""

from collections.abc import Iterator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _fake_image_provider(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep tests off remote image services even when ``.env`` selects one."""
    monkeypatch.setenv("IMAGE_PROVIDER", "fake")
    monkeypatch.setenv("ASSET_STORAGE", "local")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
