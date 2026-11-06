"""Shared file handling for backends that return image bytes over the wire.

Remote payloads are untrusted, so every write validates the magic bytes, caps
the size and records a checksum alongside the generation metadata.
"""

import base64
import binascii
import hashlib
import re
from pathlib import Path

from app.core.errors import ToolError
from app.tools.image_models import GeneratedImage

MAX_IMAGE_BYTES = 20 * 1024 * 1024

_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
)


def decode_base64(payload: str) -> bytes:
    """Decode an API payload without trusting its encoding or size."""
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ToolError("image response was not valid base64", retryable=False) from exc
    return validate_image_bytes(data)


def validate_image_bytes(data: bytes) -> bytes:
    """Reject empty, oversized or unsupported image payloads."""
    if not data:
        raise ToolError("image response was empty", retryable=False)
    if len(data) > MAX_IMAGE_BYTES:
        raise ToolError(
            "image response exceeded the size limit",
            retryable=False,
            details={"bytes": len(data), "limit": MAX_IMAGE_BYTES},
        )
    if not any(data.startswith(signature) for signature, _ in _SIGNATURES) and not (
        data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    ):
        raise ToolError("image response was not PNG, JPEG or WebP", retryable=False)
    return data


def image_extension(data: bytes) -> str:
    """Return the suffix for a supported image, rejecting anything else."""
    for signature, suffix in _SIGNATURES:
        if data.startswith(signature):
            return suffix
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise ToolError("image response was not PNG, JPEG or WebP", retryable=False)


def read_source(image_path: Path, asset_dir: Path) -> bytes:
    """Read an edit source only from inside the configured asset directory."""
    root = asset_dir.resolve()
    candidate = image_path if image_path.is_absolute() else root / image_path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ToolError(
            f"image path must be inside the asset directory: {image_path}",
            details={"path": str(image_path), "asset_dir": str(root)},
        )
    try:
        return resolved.read_bytes()
    except OSError as exc:
        raise ToolError(
            f"could not read image: {image_path}",
            details={"path": str(image_path)},
        ) from exc


def write_image(
    data: bytes,
    *,
    asset_dir: Path,
    key: str,
    model: str,
    seed: int,
    prompt: str,
) -> GeneratedImage:
    """Persist validated bytes with a deterministic, path-safe file name."""
    suffix = image_extension(data)
    safe_model = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-") or "image"
    digest = hashlib.sha256(key.encode()).hexdigest()
    asset_dir.mkdir(parents=True, exist_ok=True)
    path = asset_dir / f"{safe_model}-{digest[:16]}{suffix}"
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise ToolError(
            f"could not write image: {path}",
            details={"path": str(path)},
        ) from exc
    return GeneratedImage(
        path=path,
        checksum=hashlib.sha256(data).hexdigest(),
        model=model,
        seed=seed,
        prompt=prompt,
    )
