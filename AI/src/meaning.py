"""Meaning similarity for criterion credit. Exact wording is not required."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Checked against a Vietnamese paraphrase of the hashCode contract (0.88 → full credit)
# and an unrelated sentence (0.04 → no credit).
_BANDS = ((0.84, 1.0), (0.76, 0.75), (0.68, 0.5), (0.66, 0.25))


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def credit_from_similarity(score: float) -> float:
    for minimum, credit in _BANDS:
        if score >= minimum:
            return credit
    return 0.0


def criterion_similarities(answer: str, criterion: dict) -> tuple[float, float]:
    """Return (best similarity to a correct reference, best similarity to a misconception)."""
    positive = [*(criterion.get("reference_answers") or []), criterion.get("label") or ""]
    negative = list(criterion.get("misconceptions") or [])
    texts = [text.strip() for text in [*positive, *negative] if text and str(text).strip()]
    if not texts:
        return 0.0, 0.0
    vectors = _model().encode([answer, *texts], normalize_embeddings=True)
    answer_vector = np.asarray(vectors[0])
    scores = [float(np.dot(answer_vector, np.asarray(vectors[index + 1]))) for index in range(len(texts))]
    split = len([text for text in positive if text and str(text).strip()])
    positive_scores = scores[:split] or [0.0]
    negative_scores = scores[split:] or [0.0]
    return max(positive_scores), max(negative_scores)
