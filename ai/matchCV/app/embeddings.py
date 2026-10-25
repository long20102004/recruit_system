"""Shared embedding and cosine-similarity helpers."""

from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Lazy-load a multilingual Sentence Transformer and provide a safe fallback."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self._model = None
        self._load_attempted = False

    def _load_model(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        if os.getenv("MATCHMAKING_EMBEDDING_BACKEND", "sentence-transformers") == "hash":
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        except (ImportError, OSError, RuntimeError) as exc:
            logger.warning("Could not load embedding model %s: %s; using local fallback", self.model_name, exc)

    def encode(self, texts: list[str]) -> np.ndarray:
        self._load_model()
        if self._model is not None:
            return np.asarray(self._model.encode(texts, normalize_embeddings=True))
        return np.asarray([self._hash_embedding(text) for text in texts], dtype=np.float32)

    @staticmethod
    @lru_cache(maxsize=2048)
    def _hash_embedding(text: str, dimensions: int = 384) -> tuple[float, ...]:
        vector = np.zeros(dimensions, dtype=np.float32)
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = np.linalg.norm(vector)
        if norm:
            vector /= norm
        return tuple(float(value) for value in vector)


embedding_service = EmbeddingService()


def cosine_similarity(left: str, right: str) -> float:
    """Return a non-negative cosine similarity for two pieces of text."""
    if not left.strip() or not right.strip():
        return 0.0
    vectors = embedding_service.encode([left, right])
    similarity = float(np.dot(vectors[0], vectors[1]))
    return max(0.0, min(1.0, similarity))
