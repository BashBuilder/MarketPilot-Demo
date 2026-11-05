"""Deterministic fake and hosted HuggingFace embedder behaviour."""

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.database.models import EMBEDDING_DIMENSIONS
from app.llm.embeddings import (
    DEFAULT_HF_MODEL,
    FakeEmbedder,
    HuggingFaceEmbedder,
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


def test_fake_mode_never_imports_the_huggingface_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(_: str) -> None:
        raise AssertionError("fake mode must not import langchain-huggingface")

    monkeypatch.setattr("app.llm.embeddings.import_module", explode)

    assert isinstance(get_embedder("fake"), FakeEmbedder)


def test_huggingface_embedder_requires_a_token() -> None:
    with pytest.raises(RuntimeError, match="HUGGINGFACEHUB_API_TOKEN"):
        HuggingFaceEmbedder(DEFAULT_HF_MODEL, None)


async def test_huggingface_embedder_wraps_the_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeEndpoint:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1) for _ in texts]

    monkeypatch.setattr(
        "app.llm.embeddings.import_module",
        lambda _: SimpleNamespace(HuggingFaceEndpointEmbeddings=FakeEndpoint),
    )

    embedder = HuggingFaceEmbedder(DEFAULT_HF_MODEL, SecretStr("test-token"))
    vectors = await embedder.embed(["policy", "claims"])

    assert captured == {
        "model": DEFAULT_HF_MODEL,
        "task": "feature-extraction",
        "huggingfacehub_api_token": "test-token",
    }
    assert embedder.name == f"huggingface:{DEFAULT_HF_MODEL}"
    assert len(vectors) == 2
    assert len(vectors[0]) == EMBEDDING_DIMENSIONS


async def test_huggingface_embedder_rejects_wrong_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class WrongEndpoint:
        def __init__(self, **_: object) -> None:
            pass

        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(
        "app.llm.embeddings.import_module",
        lambda _: SimpleNamespace(HuggingFaceEndpointEmbeddings=WrongEndpoint),
    )

    embedder = HuggingFaceEmbedder(DEFAULT_HF_MODEL, SecretStr("test-token"))

    with pytest.raises(RuntimeError, match="expected"):
        await embedder.embed(["policy"])
