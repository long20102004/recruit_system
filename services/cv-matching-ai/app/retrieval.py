"""Hybrid lexical and semantic retrieval for candidate batches."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from .embeddings import embedding_service

TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


def hybrid_retrieve(
    jd_text: str,
    candidates: Sequence[dict[str, Any]],
    embed_fn: Callable[[str], np.ndarray] | None = None,
    top_k: int = 50,
) -> list[dict[str, Any]]:
    """Rank candidates with Reciprocal Rank Fusion of BM25 and embeddings."""
    if top_k <= 0:
        return []
    if not candidates:
        return []

    texts = [str(candidate.get("text", "")) for candidate in candidates]
    corpus = [_tokens(text) for text in texts]
    bm25_scores = BM25Okapi(corpus).get_scores(_tokens(jd_text))

    encode = embed_fn or (lambda text: embedding_service.encode([text])[0])
    jd_vector = np.asarray(encode(jd_text))
    semantic_scores = [
        _cosine_vectors(jd_vector, np.asarray(encode(text))) for text in texts
    ]

    bm25_ranks = np.argsort(-np.asarray(bm25_scores), kind="stable")
    semantic_ranks = np.argsort(-np.asarray(semantic_scores), kind="stable")
    rrf_scores: dict[int, float] = {}
    for ranks in (bm25_ranks, semantic_ranks):
        for rank, index in enumerate(ranks):
            rrf_scores[int(index)] = rrf_scores.get(int(index), 0.0) + 1 / (60 + rank + 1)

    ranked_indices = sorted(rrf_scores, key=lambda index: (-rrf_scores[index], index))[:top_k]
    return [
        {**candidates[index], "retrieval_score": round(rrf_scores[index], 6)}
        for index in ranked_indices
    ]


def _cosine_vectors(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = np.linalg.norm(left)
    right_norm = np.linalg.norm(right)
    if not left_norm or not right_norm:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))
