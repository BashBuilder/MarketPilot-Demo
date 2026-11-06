"""Cloudinary-backed asset storage.

Uploads are content-addressed: the public id is derived from the image checksum,
so re-uploading the same bytes is idempotent. Remote payloads are untrusted, so
a download is validated and size-capped with the same helpers the image
providers use.
"""

import hashlib
import re
from pathlib import Path

import httpx

from app.core.errors import ToolError
from app.tools.asset_storage import LocalAssetStorage
from app.tools.cloudinary_client import CloudinaryClient
from app.tools.image_models import GeneratedImage
from app.tools.image_providers.storage import image_extension, validate_image_bytes, write_image

_CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}


class CloudinaryAssetStorage:
    """Upload generated files and return their public HTTPS URL."""

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        asset_dir: Path,
        folder: str = "marketpilot",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._asset_dir = asset_dir
        self._folder = _safe_folder(folder)
        self._client = CloudinaryClient(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            timeout=timeout,
            transport=transport,
        )

    async def publish(self, image: GeneratedImage) -> str:
        data = _read(image.path)
        if hashlib.sha256(data).hexdigest() != image.checksum.lower():
            raise ToolError(
                "asset checksum mismatch before upload",
                retryable=False,
                details={"path": str(image.path)},
            )

        suffix = image_extension(data)
        body = await self._client.upload(
            data,
            public_id=f"{self._folder}/{image.checksum}",
            filename=f"{image.checksum}{suffix}",
            content_type=_CONTENT_TYPES[suffix],
        )
        return _secure_url(body, expected_bytes=len(data))

    async def localize(self, uri: str) -> Path:
        """Return a local copy of ``uri``; remote assets are fetched once."""
        if not uri.startswith(("https://", "http://")):
            return await LocalAssetStorage(self._asset_dir).localize(uri)

        data = validate_image_bytes(await self._client.download(uri))
        return write_image(
            data,
            asset_dir=self._asset_dir,
            key=f"download:{hashlib.sha256(data).hexdigest()}",
            model="cloudinary",
            seed=0,
            prompt=f"downloaded asset {uri}",
        ).path


def _secure_url(body: dict[str, object], *, expected_bytes: int) -> str:
    url = body.get("secure_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ToolError("Cloudinary response is missing a secure_url")
    uploaded = body.get("bytes")
    if isinstance(uploaded, int) and uploaded != expected_bytes:
        raise ToolError(
            "Cloudinary stored a different number of bytes than uploaded",
            retryable=False,
            details={"expected": expected_bytes, "actual": uploaded},
        )
    return url


def _safe_folder(folder: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._/-]+", "-", folder).strip("/")
    return cleaned or "marketpilot"


def _read(path: Path) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise ToolError(f"could not read image: {path}", details={"path": str(path)}) from exc
