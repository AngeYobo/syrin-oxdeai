"""Embedding provider protocol — pluggable embeddings without sentence-transformers."""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers. Use OpenAI, Cohere, or custom instead of sentence-transformers."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to embeddings. One embedding per text."""
        ...
