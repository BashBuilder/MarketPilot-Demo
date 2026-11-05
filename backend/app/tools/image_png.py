"""Minimal deterministic PNG encoding used by the fake image backend."""

import struct
import zlib

from app.tools.image_models import DEFAULT_IMAGE_SIZE, MAX_IMAGE_DIMENSION

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_bytes(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    """Encode a solid-colour RGB PNG; zlib keeps a large canvas small."""

    def chunk(tag: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return (
        PNG_SIGNATURE
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def is_png(data: bytes) -> bool:
    return data.startswith(PNG_SIGNATURE)


def png_size(data: bytes) -> tuple[int, int]:
    """Read IHDR dimensions, falling back when the header is unusable."""
    if is_png(data) and data[12:16] == b"IHDR":
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if 1 <= width <= MAX_IMAGE_DIMENSION and 1 <= height <= MAX_IMAGE_DIMENSION:
            return width, height
    return DEFAULT_IMAGE_SIZE


def color_for_seed(seed: int) -> tuple[int, int, int]:
    return (
        (seed * 37 + 11) % 256,
        (seed * 101 + 23) % 256,
        (seed * 197 + 47) % 256,
    )
