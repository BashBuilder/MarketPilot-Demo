"""Deterministic fake and guarded local embedder behaviour."""

from types import SimpleNamespace

import pytest

from app.database.models import EMBEDDING_DIMENSIONS
from app.llm.embeddings import (
    LOCAL_MODEL_NAME,
    FakeEmbedder,
    LocalEmbedder,
    get_embedder,
)


async def test_same_text_produces_the_same_vector() -> None:
    embedder = FakeEmbedder()

    first, second = await embedder.embed(["medical claims", "medical claims"])

    assert first == second


async def test_different_text_produces_a_different_vector() -> None:
    embedder = FakeEmbedder()

    medical, minors = await embedder.embed(["medical claims", "minors and likeness"])

    assert medical != minors


async def test_vectors_have_the_configured_dimension_and_unit_norm() -> None:
    vector = (await FakeEmbedder().embed(["guaranteed results"]))[0]

    assert len(vector) == EMBEDDING_DIMENSIONS
    assert sum(value * value for value in vector) == pytest.approx(1.0)


async def test_empty_text_still_produces_a_non_zero_vector() -> None:
    vector = (await FakeEmbedder().embed([""]))[0]

    assert any(value != 0.0 for value in vector)


def test_dimensions_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        FakeEmbedder(dimensions=0)


def test_fake_mode_never_imports_the_local_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(_: str) -> None:
        raise AssertionError("fake mode must not import sentence-transformers")

    monkeypatch.setattr("app.llm.embeddings.import_module", explode)

    assert isinstance(get_embedder("fake"), FakeEmbedder)


def test_local_embedder_never_downloads_a_missing_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class MissingModel:
        def __init__(self, name: str, **kwargs: object) -> None:
            captured["name"] = name
            captured["kwargs"] = kwargs
            raise OSError("not cached")

    monkeypatch.setattr(
        "app.llm.embeddings.import_module",
        lambda _: SimpleNamespace(SentenceTransformer=MissingModel),
    )

    with pytest.raises(RuntimeError, match="never downloads"):
        LocalEmbedder()

    assert captured["name"] == LOCAL_MODEL_NAME
    assert captured["kwargs"] == {
        "local_files_only": True,
    }


async def test_local_embedder_wraps_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModel:
        def __init__(self, name: str, *, local_files_only: bool) -> None:
            assert name == LOCAL_MODEL_NAME
            assert local_files_only is True

        def get_sentence_embedding_dimension(self) -> int:
            return EMBEDDING_DIMENSIONS

        def encode(self, texts: list[str], **_: object) -> list[list[float]]:
            return [[1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1) for _ in texts]

    monkeypatch.setattr(
        "app.llm.embeddings.import_module",
        lambda _: SimpleNamespace(SentenceTransformer=FakeModel),
    )

    vectors = await LocalEmbedder().embed(["policy", "claims"])

    assert len(vectors) == 2
    assert len(vectors[0]) == EMBEDDING_DIMENSIONS
