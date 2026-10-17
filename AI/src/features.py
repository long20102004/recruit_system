"""Tính feature: BERTScore (hoặc fast lexical) + coverage."""

from __future__ import annotations

from typing import Any

import numpy as np

from .coverage import normalize, score_coverage


def _token_set(text: str) -> set[str]:
    return {t for t in normalize(text).replace(",", " ").split() if len(t) > 1}


def lexical_prf(answer: str, reference: str) -> tuple[float, float, float]:
    """Fast mode: Precision/Recall/F1 theo overlap token (không cần GPU/model)."""
    a, r = _token_set(answer), _token_set(reference)
    if not a and not r:
        return 0.0, 0.0, 0.0
    if not a or not r:
        return 0.0, 0.0, 0.0
    inter = len(a & r)
    p = inter / len(a)
    rec = inter / len(r)
    f1 = 0.0 if p + rec == 0 else 2 * p * rec / (p + rec)
    return float(p), float(rec), float(f1)


def bertscore_prf(
    answers: list[str],
    references: list[str],
    model_type: str = "bert-base-multilingual-cased",
    batch_size: int = 8,
    device: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """BERTScore thật — lần đầu sẽ tải model (~700MB)."""
    from bert_score import score as bert_score_fn

    kwargs: dict[str, Any] = {
        "model_type": model_type,
        "lang": "en",  # multilingual checkpoint; lang hint ít ảnh hưởng với model_type cố định
        "verbose": True,
        "batch_size": batch_size,
        "rescale_with_baseline": False,
    }
    if device:
        kwargs["device"] = device
    P, R, F1 = bert_score_fn(answers, references, **kwargs)
    return P.numpy(), R.numpy(), F1.numpy()


def build_feature_row(
    answer: str,
    question: dict[str, Any],
    p: float,
    r: float,
    f1: float,
) -> dict[str, Any]:
    cov = score_coverage(answer, question["criteria"])
    length_norm = min(len(answer) / 300.0, 1.0)
    return {
        "bert_P": round(float(p), 4),
        "bert_R": round(float(r), 4),
        "bert_F1": round(float(f1), 4),
        "coverage_score": cov["coverage_score"],
        "length_norm": round(length_norm, 4),
        "covered_keys": ";".join(cov["covered_keys"]),
        "missing_keys": ";".join(cov["missing_keys"]),
        "covered_labels": cov["covered_labels"],
        "missing_labels": cov["missing_labels"],
    }


FEATURE_COLUMNS = ["bert_P", "bert_R", "bert_F1", "coverage_score", "length_norm"]
