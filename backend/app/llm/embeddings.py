"""Embedding selection: deterministic fake or hosted HuggingFace endpoint."""

import hashlib
import math
import re
from importlib import import_module
from typing import Any, Protocol

from pydantic import SecretStr

from app.core.config import EmbedderName, get_settings
from app.database.models import EMBEDDING_DIMENSIONS

DEFAULT_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

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


class HuggingFaceEmbedder:
    """LangChain adapter for the hosted HuggingFace feature-extraction API.

    No model files are downloaded and torch is not imported. The optional
    LangChain integration is imported lazily so fake mode stays dependency-free.
    """

    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, model: str, token: SecretStr | None) -> None:
        if token is None or not token.get_secret_value():
            raise RuntimeError("EMBEDDER=huggingface requires HUGGINGFACEHUB_API_TOKEN")

        self.name = f"huggingface:{model}"
        try:
            module = import_module("langchain_huggingface")
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDER=huggingface requires langchain-huggingface; "
                "install it with 'uv sync --extra embeddings'"
            ) from exc

        endpoint_type = module.HuggingFaceEndpointEmbeddings
        self._embeddings: Any = endpoint_type(
            model=model,
            task="feature-extraction",
            huggingfacehub_api_token=token.get_secret_value(),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            raw: Any = await self._embeddings.aembed_documents(texts)
        except Exception as exc:
            raise RuntimeError(f"HuggingFace embedding request failed for {self.name}") from exc

        vectors = [[float(value) for value in vector] for vector in raw]
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise RuntimeError(
                    f"{self.name} returned {len(vector)} dimensions; expected {self.dimensions}"
                )
        return vectors


def get_embedder(name: EmbedderName | None = None) -> Embedder:
    """Return the configured embedder, defaulting to the deterministic fake."""
    if name == "fake":
        return FakeEmbedder()

    settings = get_settings()
    selected = name if name is not None else settings.embedder
    if selected == "huggingface":
        return HuggingFaceEmbedder(
            settings.hf_embedding_model,
            settings.huggingfacehub_api_token,
        )
    return FakeEmbedder()
