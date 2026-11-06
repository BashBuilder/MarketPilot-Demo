"""Select the configured image backend behind the ``ImageGenerator`` protocol."""

from app.core.config import Settings
from app.tools.image_models import ImageGenerator
from app.tools.image_providers.hosted import HostedImageGenerator
from app.tools.image_providers.huggingface import HuggingFaceImageGenerator
from app.tools.image_tools import FakeImageGenerator


def build_image_generator(settings: Settings) -> ImageGenerator:
    """Return the backend named by ``IMAGE_PROVIDER``.

    Configuration is validated here, not at request time, so a hosted setup
    with a missing URL or key fails before a run starts.
    """
    if settings.image_provider == "fake":
        return FakeImageGenerator(settings.asset_dir)

    if settings.image_provider == "hosted":
        url = (settings.image_api_url or "").strip()
        key = settings.image_api_key.get_secret_value() if settings.image_api_key else ""
        if not url or not key:
            raise RuntimeError("IMAGE_PROVIDER=hosted requires IMAGE_API_URL and IMAGE_API_KEY")
        return HostedImageGenerator(
            api_url=url,
            api_key=key,
            asset_dir=settings.asset_dir,
            timeout=settings.image_timeout_seconds,
        )

    if settings.image_provider == "huggingface":
        token = (
            settings.huggingfacehub_api_token.get_secret_value()
            if settings.huggingfacehub_api_token
            else ""
        )
        if not token:
            raise RuntimeError("IMAGE_PROVIDER=huggingface requires HUGGINGFACEHUB_API_TOKEN")
        return HuggingFaceImageGenerator(
            model_id=settings.image_model_id,
            api_key=token,
            asset_dir=settings.asset_dir,
            timeout=settings.image_timeout_seconds,
        )

    raise RuntimeError(f"unsupported IMAGE_PROVIDER: {settings.image_provider}")
