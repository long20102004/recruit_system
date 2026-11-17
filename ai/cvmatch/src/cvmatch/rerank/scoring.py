"""RR4: thieu du lieu -> diem tho -> cong must-have -> diem 0-100 -> xep hang (thiet ke 07 muc 5.8-5.10).

    S_raw = sum_f w_f f / sum_f w_f        (f: feature bat va kha dung)
    score = round(min(100 S_raw, gate_cap))
    xep hang: score giam -> S_raw giam -> A1 giam -> cv_id tang
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from cvmatch.core.config import RerankConfig
from cvmatch.core.contracts import FEATURES


@dataclass
class Scored:
    item_id: str
    raw: dict[str, float | None]                    # gia tri feature truoc khi dien
    missing: dict[str, str]                         # feature -> 'jd_side' | 'cv_side'
    used: dict[str, float | None] = field(default_factory=dict)   # gia tri dung de cham (sau 5.8)
    s_raw: float = 0.0
    gate_cap: int = 100
    score: int = 0
    flags: list[str] = field(default_factory=list)
    rank: int = 0

    @property
    def cap_applied(self) -> bool:
        return 100 * self.s_raw > self.gate_cap


def fill_missing(rows: list[Scored], cfg: RerankConfig) -> None:
    """5.8: jd_side -> bo feature cho moi CV; cv_side -> trung vi pool | bo ra | 0."""
    enabled = [f for f in FEATURES if f in cfg.features_enabled]
    policy = cfg.missing.cv_side_policy
    medians: dict[str, float | None] = {}
    for f in enabled:
        vals = [r.raw[f] for r in rows if r.raw.get(f) is not None]
        medians[f] = float(np.median(vals)) if vals else None
    for r in rows:
        used: dict[str, float | None] = {}
        for f in enabled:
            v = r.raw.get(f)
            side = r.missing.get(f)
            if v is None and side == "cv_side":
                v = {"pool_median": medians[f], "zero": 0.0, "drop": None}[policy]
            used[f] = v
        r.used = used
        n_cv = sum(1 for f in enabled if r.missing.get(f) == "cv_side")
        if n_cv >= cfg.low_data_quality.min_missing and "low_data_quality" not in r.flags:
            r.flags.append("low_data_quality")


def gate_cap(a1: float | None, cfg: RerankConfig) -> int:
    if a1 is None:
        return 100
    t_lo, t_hi = cfg.gate.thresholds
    c_lo, c_hi = cfg.gate.caps
    if a1 < t_lo:
        return c_lo
    if a1 < t_hi:
        return c_hi
    return 100


def s_raw(used: dict[str, float | None], weights: dict[str, float]) -> float:
    num = den = 0.0
    for f, v in used.items():
        if v is None:
            continue
        num += weights[f] * v
        den += weights[f]
    return num / den if den > 0 else 0.0


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5 + 1e-9))


def finalize(rows: list[Scored], cfg: RerankConfig) -> list[Scored]:
    """Dien thieu, tinh diem, xep hang (gan `rank` cho moi dong). Tra danh sach da xep."""
    fill_missing(rows, cfg)
    for r in rows:
        r.s_raw = s_raw(r.used, cfg.weights)
        r.gate_cap = gate_cap(r.used.get("A1"), cfg)
        r.score = max(0, min(100, _round_half_up(min(100 * r.s_raw, r.gate_cap))))
        if r.cap_applied and "cap_applied" not in r.flags:
            r.flags.append("cap_applied")
    a1 = lambda r: r.used.get("A1") if r.used.get("A1") is not None else -1.0  # noqa: E731
    ordered = sorted(rows, key=lambda r: (-r.score, -r.s_raw, -a1(r), r.item_id))
    for k, r in enumerate(ordered, start=1):
        r.rank = k
    return ordered


def band(score: int, cfg: RerankConfig) -> str:
    hi, mid = cfg.score.bands
    return "high" if score >= hi else "mid" if score >= mid else "low"
