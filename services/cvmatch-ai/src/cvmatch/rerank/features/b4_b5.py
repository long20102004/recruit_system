"""B4 (trach nhiem) va B5 (yeu cau dang chu) tu ma tran BERTScore R (thiet ke 07 muc 5.3, 5.4).

    cal_ij = clip((R_ij - lo) / (hi - lo), 0, 1) x m_i
    m_i    = m_negation neu gach co has_negation · m_coursework neu is_coursework · 1 con lai
    c_j    = max_i cal_ij        best_j = argmax_i cal_ij
    B      = sum_j w_j c_j / sum_j w_j      (w_j = 1, cau generic = b4.generic_weight)

Ham thuan tren numpy; can khop tu (align) do `rerank.run` goi rieng cho cap (j, best_j).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvmatch.core.config import B4Config


def calibrate(R: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.clip((R - lo) / (hi - lo), 0.0, 1.0)


def bullet_multipliers(has_negation: np.ndarray, is_coursework: np.ndarray, cfg: B4Config) -> np.ndarray:
    """Phu dinh uu tien hon hoc/lam (gach co ca hai -> m_negation)."""
    m = np.ones(len(has_negation), dtype=np.float32)
    m[np.asarray(is_coursework, bool)] = cfg.m_coursework
    m[np.asarray(has_negation, bool)] = cfg.m_negation
    return m


def level_of(c: float, cfg: B4Config) -> str:
    if c >= cfg.level.met:
        return "met"
    if c >= cfg.level.partial:
        return "partial"
    return "not_evidenced"


@dataclass
class SentenceScores:
    c: np.ndarray        # (|J|,) c_j
    best: np.ndarray     # (|J|,) chi so gach tot nhat trong CV, -1 neu c_j = 0 (khong co bang chung)
    R_best: np.ndarray   # (|J|,) R tho cua gach tot nhat (0 neu khong co)
    cal: np.ndarray      # (|J|, |I|)


def calibrated(R: np.ndarray, cfg: B4Config, cos: np.ndarray | None = None) -> np.ndarray:
    """Ma tran da hieu chuan theo `b4.engine` (R-E2, R-E10): bertscore -> calib(R);
    cosine -> cos_calib(cos); max -> max cua hai. `cos`: cosine cau dense (|J|, |I|)."""
    if cfg.engine == "bertscore" or cos is None:
        return calibrate(R, cfg.calib.lo, cfg.calib.hi)
    c = calibrate(cos, cfg.cos_calib.lo, cfg.cos_calib.hi)
    if cfg.engine == "cosine":
        return c
    return np.maximum(calibrate(R, cfg.calib.lo, cfg.calib.hi), c)


def sentence_scores(R: np.ndarray, m: np.ndarray, cfg: B4Config, cal_base: np.ndarray | None = None) -> SentenceScores:
    """R: (|J|, |I|) cua MOT CV; m: (|I|,). `cal_base`: ma tran da hieu chuan (mac dinh calib(R))."""
    J, I = R.shape
    if I == 0:
        z = np.zeros(J, np.float32)
        return SentenceScores(z, np.full(J, -1), z.copy(), np.zeros((J, 0), np.float32))
    cal = (calibrate(R, cfg.calib.lo, cfg.calib.hi) if cal_base is None else cal_base) * m[None, :]
    # argmax tat dinh: cal lon nhat, hoa thi R lon hon, roi chi so nho hon
    best = np.array([np.lexsort((-R[j], -cal[j]))[0] for j in range(J)], dtype=np.int64) if J else np.zeros(0, int)
    c = cal[np.arange(J), best].astype(np.float32) if J else np.zeros(0, np.float32)
    R_best = R[np.arange(J), best].astype(np.float32) if J else np.zeros(0, np.float32)
    best = np.where(c > 0, best, -1)
    R_best = np.where(c > 0, R_best, 0.0).astype(np.float32)
    return SentenceScores(c, best, R_best, cal)


def sentence_weights(is_generic: list[bool], generic_weight: float) -> np.ndarray:
    return np.array([generic_weight if g else 1.0 for g in is_generic], dtype=np.float32)


def aggregate(c: np.ndarray, w: np.ndarray) -> float | None:
    """Trung binh co trong so; khong con cau nao co trong so > 0 -> None (thieu phia JD)."""
    if not len(w) or float(w.sum()) <= 0:
        return None
    return float((c * w).sum() / w.sum())
