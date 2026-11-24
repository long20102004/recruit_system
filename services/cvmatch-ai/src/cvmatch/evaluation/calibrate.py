"""Hieu chuan B4 tu tap ~300 cap (trach nhiem, gach) co nhan (thiet ke 07 muc 5.3, 09 muc 2, R-E5).

    lo = trung vi R cua cap `khong`      hi = trung vi R cua cap `khop`
    nguong muc khop (met / partial) tren c = clip((R - lo) / (hi - lo)): chon cap nguong tren luoi 0,05
    sao cho do chinh xac trung binh 3 lop (khop / mot_phan / khong) cao nhat.
Kem AUC (khop vs khong) cua R (BERTScore, token) va cosine cau (dense) - so truc tiep hai do phan giai.
Chi IN gia tri de nguoi dung dua vao config moi (vd `rr-1.2.yaml`), KHONG tu sua.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvmatch.evaluation.labels import PairLabel
from cvmatch.evaluation.metrics import auc
from cvmatch.rerank.bertscore.engine import BertScorer


@dataclass
class Calibration:
    n: dict[str, int]
    lo: float | None
    hi: float | None
    met: float | None
    partial: float | None
    balanced_acc: float | None
    auc_bertscore: float | None
    auc_cosine: float | None
    R: list[float]
    cos: list[float | None]
    labels: list[str]

    def yaml_snippet(self) -> str:
        if self.lo is None or self.hi is None:
            return "# chua du cap `khop` va `khong` de hieu chuan"
        return (f"b4:\n  calib: {{lo: {self.lo:.4f}, hi: {self.hi:.4f}}}       # trung vi R cap khong / khop"
                f" (n = {self.n.get('khong', 0)} / {self.n.get('khop', 0)})\n"
                f"  level: {{met: {self.met:.2f}, partial: {self.partial:.2f}}}   # do chinh xac can bang"
                f" {self.balanced_acc:.3f}\n")


def _balanced_acc(c: np.ndarray, labs: list[str], met: float, partial: float) -> float:
    pred = np.where(c >= met, "khop", np.where(c >= partial, "mot_phan", "khong"))
    accs = []
    for lab in ("khop", "mot_phan", "khong"):
        idx = [i for i, x in enumerate(labs) if x == lab]
        if idx:
            accs.append(float(np.mean([pred[i] == lab for i in idx])))
    return float(np.mean(accs)) if accs else 0.0


def calibrate_pairs(pairs: list[PairLabel], scorer: BertScorer, *, encoder=None, step: float = 0.05) -> Calibration:
    jd_t = [p.jd_text for p in pairs]
    cv_t = [p.cv_text for p in pairs]
    labs = [p.label for p in pairs]
    jd_e = scorer.embed(scorer.prepare(jd_t))
    cv_e = scorer.embed(scorer.prepare(cv_t))
    R = np.array([float(scorer.score_embs([a], [b])[0, 0]) for a, b in zip(jd_e, cv_e)], dtype=np.float64)
    cos: list[float | None] = [None] * len(pairs)
    if encoder is not None and pairs:
        ej = encoder.encode(jd_t).dense
        ec = encoder.encode(cv_t).dense
        cos = [float(np.dot(a, b)) for a, b in zip(ej, ec)]
    n = {lab: labs.count(lab) for lab in ("khop", "mot_phan", "khong")}
    r_k = [R[i] for i, x in enumerate(labs) if x == "khop"]
    r_n = [R[i] for i, x in enumerate(labs) if x == "khong"]
    pos = [x == "khop" for x in labs]
    keep = [i for i, x in enumerate(labs) if x != "mot_phan"]
    a_bert = auc([R[i] for i in keep], [pos[i] for i in keep])
    a_cos = auc([cos[i] for i in keep], [pos[i] for i in keep]) if cos[0] is not None else None
    if not r_k or not r_n or np.median(r_k) <= np.median(r_n):
        return Calibration(n, None, None, None, None, None, a_bert, a_cos, R.tolist(), cos, labs)
    lo, hi = float(np.median(r_n)), float(np.median(r_k))
    c = np.clip((R - lo) / (hi - lo), 0, 1)
    grid = np.round(np.arange(step, 1.0 + 1e-9, step), 4)
    best = (-1.0, 0.6, 0.3)
    for met in grid:
        for partial in grid[grid < met]:
            acc = _balanced_acc(c, labs, float(met), float(partial))
            # hoa: uu tien nguong gan mac dinh (0,6 / 0,3) cho on dinh
            key = (acc, -abs(met - 0.6) - abs(partial - 0.3))
            if key > (best[0], -abs(best[1] - 0.6) - abs(best[2] - 0.3)):
                best = (acc, float(met), float(partial))
    return Calibration(n, lo, hi, best[1], best[2], best[0], a_bert, a_cos, R.tolist(), cos, labs)
