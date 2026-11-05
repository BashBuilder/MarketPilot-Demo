"""Embedding abstraction with a deterministic fake for tests and local dev."""

import hashlib
import math
import re
from typing import Protocol

from app.database.models import EMBEDDING_DIMENSIONS

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    """Turns text into vectors of a fixed dimension."""

    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbedder:
    """Hashes tokens into signed vector slots.

    Token-level hashing keeps texts that share words close together, so policy
    retrieval tests exercise real ranking rather than random similarity.
    """

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = _TOKEN_RE.findall(text.lower()) or [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            # Cancelling collisions must not produce a vector cosine cannot rank.
            index = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")
            vector[index % self.dimensions] = 1.0
            return vector
        return [value / norm for value in vector]


def get_embedder() -> Embedder:
    """Return the active embedder; only the fake exists until a model is chosen."""
    return FakeEmbedder()
