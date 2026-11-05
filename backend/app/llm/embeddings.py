"""Embedding abstraction with a deterministic fake and an optional local model."""

import asyncio
import hashlib
import math
import re
from importlib import import_module
from typing import Any, Protocol

from app.core.config import EmbedderName, get_settings
from app.database.models import EMBEDDING_DIMENSIONS

LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LOCAL_MODEL_SIZE = "~90 MB"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    """Turns text into vectors of a fixed dimension."""

    name: str
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbedder:
    """Hashes tokens into signed vector slots.

    Token-level hashing keeps texts that share words close together, so policy
    retrieval tests exercise real ranking rather than random similarity.
    """

    name = "fake"

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


class LocalEmbedder:
    """Sentence-transformers adapter that never downloads a model implicitly.

    The optional dependency is imported lazily so fake mode and tests do not
    load torch. ``local_files_only`` makes a missing cache a clear configuration
    error instead of an unexpected network transfer.
    """

    name = LOCAL_MODEL_NAME
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        try:
            module = import_module("sentence_transformers")
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDER=local requires sentence-transformers; "
                "install it with 'uv sync --extra embeddings'"
            ) from exc

        model_type = module.SentenceTransformer
        try:
            self._model: Any = model_type(LOCAL_MODEL_NAME, local_files_only=True)
        except Exception as exc:
            raise RuntimeError(
                f"local embedding model is not available: {LOCAL_MODEL_NAME} "
                f"({LOCAL_MODEL_SIZE}). Download it explicitly before starting "
                "the service; the application never downloads models automatically."
            ) from exc

        actual = int(self._model.get_sentence_embedding_dimension())
        if actual != self.dimensions:
            raise RuntimeError(
                f"{LOCAL_MODEL_NAME} returns {actual} dimensions; expected {self.dimensions}"
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        raw: Any = await asyncio.to_thread(
            self._model.encode,
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector] for vector in raw]


def get_embedder(name: EmbedderName | None = None) -> Embedder:
    """Return the configured embedder, defaulting to the deterministic fake."""
    selected = name if name is not None else get_settings().embedder
    if selected == "local":
        return LocalEmbedder()
    return FakeEmbedder()
