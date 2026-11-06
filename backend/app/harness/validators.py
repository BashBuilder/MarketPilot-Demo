"""Semantic checks for briefs, copy and generated assets.

These live apart from the verification loop: each validator knows one output
type and returns human-readable issues, without caring how retries happen.
"""

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from app.agents.outputs import AdCopySet, AssetSet, AudienceResearch, CampaignBrief

type Issue = str

MAX_HEADLINE_LENGTH: Final[int] = 40

_IMAGE_SIGNATURES: Final[tuple[bytes, ...]] = (
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
)


class BriefSemanticValidator:
    """Reject a brief that does not say what, why, for whom, or where."""

    def validate(self, value: CampaignBrief) -> list[Issue]:
        issues: list[Issue] = []
        for field in ("product", "goal", "audience"):
            if not getattr(value, field).strip():
                issues.append(f"{field} must not be empty")
        if not value.channels:
            issues.append("at least one channel is required")
        return issues


class ResearchSourceValidator:
    """Reject citations the search tool did not return in this run."""

    def __init__(self, retrieved_urls: Iterable[str]) -> None:
        self._retrieved = {_normalize_url(url) for url in retrieved_urls}

    def validate(self, value: AudienceResearch) -> list[Issue]:
        issues: list[Issue] = []
        for source in value.sources:
            url = str(source.url)
            if _normalize_url(url) not in self._retrieved:
                issues.append(f"source {url} was not retrieved by the search tool")
        return issues


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


class CopySemanticValidator:
    """Reject copy that is blank or too long to render in ad slots."""

    def validate(self, value: AdCopySet) -> list[Issue]:
        issues: list[Issue] = []
        for index, variant in enumerate(value.variants, start=1):
            label = f"variant {index} ({variant.channel})"
            for field, text in (
                ("channel", variant.channel),
                ("headline", variant.headline),
                ("description", variant.description),
                ("cta", variant.cta),
            ):
                if not text.strip():
                    issues.append(f"{label}: {field} is empty")
            headline = variant.headline.strip()
            if len(headline) > MAX_HEADLINE_LENGTH:
                issues.append(
                    f"{label}: headline is {len(headline)} characters; "
                    f"limit is {MAX_HEADLINE_LENGTH}"
                )
        return issues


class AssetSemanticValidator:
    """Confirm each asset exists, is an image, and matches its checksum.

    Remote URIs are not fetched again: the asset store validates the bytes
    (magic number, size, checksum) immediately before uploading them, so the
    stored object is the exact file this check would have inspected.
    """

    def __init__(self, asset_root: Path) -> None:
        self._root = asset_root

    def validate(self, value: AssetSet) -> list[Issue]:
        issues: list[Issue] = []
        for asset in value.assets:
            if asset.uri.startswith("https://"):
                continue
            path = self._resolve(asset.uri)
            if path is None:
                issues.append(f"asset {asset.uri!r}: unsupported uri scheme")
                continue
            if not path.is_file():
                issues.append(f"asset {asset.uri!r}: file not found at {path}")
                continue

            data = path.read_bytes()
            if not _is_image(data):
                issues.append(f"asset {asset.uri!r}: not a decodable image")
            if hashlib.sha256(data).hexdigest() != asset.checksum.lower():
                issues.append(f"asset {asset.uri!r}: checksum mismatch")
        return issues

    def _resolve(self, uri: str) -> Path | None:
        if "://" in uri:
            if not uri.startswith("file://"):
                return None
            return Path(uri.removeprefix("file://"))
        path = Path(uri)
        return path if path.is_absolute() else self._root / path


def _is_image(data: bytes) -> bool:
    if data.startswith(_IMAGE_SIGNATURES):
        return True
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
