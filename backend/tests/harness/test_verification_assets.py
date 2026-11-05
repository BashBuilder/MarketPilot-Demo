"""Schema and semantic verification for generated assets."""

import base64
import hashlib
from pathlib import Path

from app.agents.outputs import Asset, AssetSet
from app.harness.verification import AssetSemanticValidator

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8"
    "BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def make_asset(name: str, *, checksum: str | None = None, uri: str | None = None) -> Asset:
    return Asset(
        uri=uri or name,
        checksum=checksum or hashlib.sha256(PNG_1X1).hexdigest(),
        model="fake",
        seed=1,
        prompt="Editorial portrait",
    )


def test_valid_image_passes(tmp_path: Path) -> None:
    (tmp_path / "hero.png").write_bytes(PNG_1X1)
    asset = make_asset("hero.png")

    issues = AssetSemanticValidator(tmp_path).validate(AssetSet(assets=[asset]))

    assert issues == []


def test_missing_file_is_reported(tmp_path: Path) -> None:
    asset = make_asset("missing.png", checksum="0" * 64)

    issues = AssetSemanticValidator(tmp_path).validate(AssetSet(assets=[asset]))

    assert issues == [f"asset 'missing.png': file not found at {tmp_path / 'missing.png'}"]


def test_non_image_bytes_are_reported(tmp_path: Path) -> None:
    data = b"this is not an image"
    (tmp_path / "hero.png").write_bytes(data)
    asset = make_asset("hero.png", checksum=hashlib.sha256(data).hexdigest())

    issues = AssetSemanticValidator(tmp_path).validate(AssetSet(assets=[asset]))

    assert issues == ["asset 'hero.png': not a decodable image"]


def test_checksum_mismatch_is_reported(tmp_path: Path) -> None:
    (tmp_path / "hero.png").write_bytes(PNG_1X1)
    asset = make_asset("hero.png", checksum="f" * 64)

    issues = AssetSemanticValidator(tmp_path).validate(AssetSet(assets=[asset]))

    assert issues == ["asset 'hero.png': checksum mismatch"]


def test_remote_uri_is_unverifiable(tmp_path: Path) -> None:
    asset = make_asset("hero.png", checksum="0" * 64, uri="s3://bucket/hero.png")

    issues = AssetSemanticValidator(tmp_path).validate(AssetSet(assets=[asset]))

    assert issues == ["asset 's3://bucket/hero.png': unsupported uri scheme"]
