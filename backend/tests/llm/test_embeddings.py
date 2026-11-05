"""Deterministic behaviour of the fake embedder."""

import pytest

from app.database.models import EMBEDDING_DIMENSIONS
from app.llm.embeddings import FakeEmbedder


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
