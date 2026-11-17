"""Chay golden test BERTScore (thiet ke 09 muc 4.2, G1/G2) va in bang nhu file 10.

- S1: nguyen JD (noi cac cau) x nguyen CV (noi cac gach).
- S2: moi cau JD x moi gach CV -> max theo CV -> trung binh qua cau JD   (cach dung o Rerank)
- S3: moi gach CV x nguyen JD -> max.
- % span = chenh lech / (diem T23 trung hoan toan − diem T10 khong lien quan), tinh rieng moi cach chia.

`bare=True`: mo hinh tran (tat doi alias, tat che so) -> phai tai tao so lieu file 10.
`bare=False`: qua buoc chuan bi dau vao cua pipeline (G2).
Dieu kien giu cau hinh (G1): S2 dat >= 25/26 va khong test nao tu Dat chuyen Khong dat.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from cvmatch.evaluation.golden.data import GOLDEN
from cvmatch.rerank.bertscore.engine import BertScorer

SPLITS = ("S1", "S2", "S3")


def split_scores(scorer: BertScorer, jd: list[str], cv: list[str]) -> dict[str, float]:
    R = scorer.recall_matrix(jd, cv)
    s1 = scorer.recall_matrix(["\n".join(jd)], ["\n".join(cv)])[0, 0]
    s3 = scorer.recall_matrix(["\n".join(jd)], cv)[0].max()
    return {"S1": float(s1), "S2": float(R.max(axis=1).mean()), "S3": float(s3)}


@dataclass
class TestResult:
    id: str
    name: str
    scores: dict[str, dict[str, float]]                       # split -> bien the -> recall
    status: dict[str, bool | None] = field(default_factory=dict)  # split -> dat / khong dat / None (ghi nhan)
    message: dict[str, str] = field(default_factory=dict)
    note: dict[str, str] = field(default_factory=dict)


@dataclass
class GoldenReport:
    bare: bool
    config_key: str
    span: dict[str, float]
    results: list[TestResult]
    seconds: float

    def passed(self, split: str = "S2") -> tuple[int, int]:
        st = [r.status.get(split) for r in self.results if r.status.get(split) is not None]
        return sum(st), len(st)

    def failed_ids(self, split: str = "S2") -> list[str]:
        return [r.id for r in self.results if r.status.get(split) is False]

    def max_diff_vs_doc(self) -> tuple[float, str]:
        worst, where = 0.0, ""
        for r in self.results:
            exp = next(t for t in GOLDEN if t["id"] == r.id).get("expected_bare", {})
            for v, e in exp.items():
                d = abs(r.scores["S2"][v] - e)
                if d > worst:
                    worst, where = d, f"{r.id}.{v}"
        return worst, where

    def to_markdown(self) -> str:
        lines = [f"# Golden test BERTScore ({'mô hình trần' if self.bare else 'qua pipeline'})", "",
                 f"`bertscore_config` = `{self.config_key}` · {self.seconds:.1f} s", "",
                 "| Cách chia | Đạt | Không đạt | span |", "|---|---|---|---|"]
        for s in SPLITS:
            p, n = self.passed(s)
            lines.append(f"| {s} | {p}/{n} | {', '.join(self.failed_ids(s)) or '-'} | {self.span[s]:.4f} |")
        if self.bare:
            d, w = self.max_diff_vs_doc()
            lines += ["", f"Lệch lớn nhất so với file 10 (Recall S2): **{d:.4f}** ở `{w}`"]
        lines += ["", "| Test | Biến thể: Recall S2 | Kết quả S2 | Ghi nhận |", "|---|---|---|---|"]
        for r in self.results:
            sc = " · ".join(f"`{k}` {v:.4f}" for k, v in r.scores["S2"].items())
            st = {True: "✅", False: "❌", None: "📝"}[r.status.get("S2")]
            lines.append(f"| {r.id} {r.name} | {sc} | {st} {r.message.get('S2', '')} | {r.note.get('S2', '')} |")
        return "\n".join(lines) + "\n"


def run_golden(scorer: BertScorer, *, bare: bool | None = None) -> GoldenReport:
    t0 = time.perf_counter()
    raw: dict[str, dict[str, dict[str, float]]] = {}
    for t in GOLDEN:
        per: dict[str, dict[str, float]] = {s: {} for s in SPLITS}
        for v, cv in t["variants"].items():
            for s, x in split_scores(scorer, t["jd"], cv).items():
                per[s][v] = x
        for v, (jd2, cv2) in t.get("extra", {}).items():
            for s, x in split_scores(scorer, jd2, cv2).items():
                per[s][v] = x
        raw[t["id"]] = per
    span = {s: raw["T23"][s]["identical"] - raw["T10"][s]["unrelated"] for s in SPLITS}

    results = []
    for t in GOLDEN:
        r = TestResult(t["id"], t["name"], raw[t["id"]])
        check = t.get("check")
        if not bare and "full_pipeline_check" in t:
            check = t["full_pipeline_check"]
        for s in SPLITS:
            if check is not None and s in t.get("check_splits", SPLITS):
                ok, msg = check(r.scores[s], span[s])
                r.status[s], r.message[s] = (bool(ok) if ok is not None else None), msg
            else:
                r.status[s] = None
            if "note" in t:
                r.note[s] = t["note"](r.scores[s], span[s])[1]
        results.append(r)
    if bare is None:
        bare = not (scorer.cfg.canonicalize_aliases or scorer.cfg.mask_numbers)
    return GoldenReport(bare, scorer.cfg.key(), span, results, time.perf_counter() - t0)


def benchmark(scorer: BertScorer, n_cv: int = 200, n_bullets: int = 8, n_resp: int = 3) -> dict:
    """Do chi phi nhu file 10: 1 JD x n_resp trach nhiem x 200 CV x 8 gach (S2). Lan lanh va lan am."""
    rng = np.random.default_rng(0)
    words = ("xây dựng tối ưu triển khai thiết kế phát triển api thanh toán truy vấn postgresql docker "
             "kubernetes kafka react java python django redis aws hệ thống dịch vụ module đơn hàng").split()
    cvs = [" ".join(rng.choice(words, 10)) + f" {k}" for k in range(n_cv * n_bullets)]
    jd = [" ".join(rng.choice(words, 8)) for _ in range(n_resp)]
    scorer.cache.__init__(scorer.cfg.key(), scorer.cache.max_bytes, scorer.cache.conn)  # cache rong
    import torch
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t = time.perf_counter()
    scorer.recall_matrix(jd, cvs)
    cold = time.perf_counter() - t
    t = time.perf_counter()
    scorer.recall_matrix(jd, cvs)
    warm = time.perf_counter() - t
    peak = torch.cuda.max_memory_allocated() / 2**20 if torch.cuda.is_available() else None
    return {"cold_s": round(cold, 2), "warm_s": round(warm, 3), "ms_per_cv_cold": round(cold / n_cv * 1000, 1),
            "peak_gpu_mb": round(peak) if peak else None, "pairs": n_cv * n_bullets * n_resp}
