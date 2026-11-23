"""Chuan hoa tung goc nhin va hop nhat (thiet ke 06 C4-C5, 01 muc 8).

- `minmax` (mac dinh): (x - min)/(max - min) tren cac CV trong pool; max = min -> 0 ca view.
- `dbsf` (thi nghiem RT-E6): (x - (mu - 3 sigma)) / (6 sigma), cat ve [0, 1].
- `score_sum` (mac dinh): trung binh co trong so cua cac view KHA DUNG cua tung CV (NaN bo qua).
- `rrf` (du phong): sum 1/(k + hang) tren cac view.
Xep hang tat dinh: fused giam -> s_skill giam -> cv_id tang.
"""

from __future__ import annotations

import numpy as np


def normalize(x: np.ndarray, mask: np.ndarray, method: str = "minmax") -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float32)
    sel = mask & np.isfinite(x)
    if not sel.any():
        return out
    v = x[sel].astype(np.float64)
    if method == "minmax":
        lo, hi = v.min(), v.max()
        out[sel] = 0.0 if hi == lo else (v - lo) / (hi - lo)
    elif method == "dbsf":
        mu, sd = v.mean(), v.std()
        out[sel] = 0.0 if sd == 0 else np.clip((v - (mu - 3 * sd)) / (6 * sd), 0, 1)
    else:
        raise ValueError(f"normalization khong ho tro: {method}")
    return out


def score_sum(normed: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    names = list(normed)
    stack = np.stack([normed[n] for n in names])                  # (V, n)
    w = np.array([weights.get(n, 1.0) for n in names], dtype=np.float64)[:, None]
    have = np.isfinite(stack)
    num = np.where(have, stack, 0.0) * w
    den = (have * w).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num.sum(axis=0) / den, np.nan).astype(np.float32)


def rrf(raw: dict[str, np.ndarray], mask: np.ndarray, k: int = 60,
        weights: dict[str, float] | None = None) -> np.ndarray:
    """RRF: sum_view w_view / (k + hang). `weights=None` -> moi view 1 (RRF thuong); RT-E2 co trong so."""
    total = np.zeros(len(mask), dtype=np.float64)
    for name, x in raw.items():
        w = 1.0 if weights is None else float(weights.get(name, 1.0))
        v = np.where(mask & np.isfinite(x), x, -np.inf)
        order = np.argsort(-v, kind="stable")
        ranks = np.empty(len(v), dtype=np.int64)
        ranks[order] = np.arange(1, len(v) + 1)
        total += np.where(np.isfinite(v), w / (k + ranks), 0.0)
    return np.where(mask, total, np.nan).astype(np.float32)


def rank(fused: np.ndarray, s_skill: np.ndarray | None, ids: list[str], mask: np.ndarray, k: int) -> np.ndarray:
    """Chi so hang trong pool sap theo fused giam, roi s_skill giam, roi cv_id tang (tat dinh)."""
    cand = np.flatnonzero(mask & np.isfinite(fused))
    sk = s_skill[cand] if s_skill is not None else np.zeros(len(cand))
    sk = np.where(np.isfinite(sk), sk, -1.0)
    id_rank = np.argsort(np.argsort(np.array([ids[i] for i in cand], dtype=object)))
    order = np.lexsort((id_rank, -sk, -fused[cand]))
    return cand[order[:k]]
