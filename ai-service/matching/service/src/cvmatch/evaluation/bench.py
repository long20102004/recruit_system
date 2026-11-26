"""S05: do thoi gian match theo co pool (V-12) - dau vao chon nguong pool nho cua S06.

Luong C voi `include_cv_ids` = n CV ngau nhien (co dinh theo seed), `K = n` de rerank TOAN BO pool (dung nhu che do
pool nho), cho tung n. Moi n chay 2 lan: lan 1 cache token BERTScore cua cac gach do chua co trong RAM (`cold`),
lan 2 da co (`warm`). Dung `Services(db_cache=False)` de cache chi o RAM -> lan 1 la lanh that.
Luong D: mot CV voi toan bo JD dang mo.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class BenchRow:
    flow: str
    n: int
    run: str          # cold | warm
    retrieve_s: float
    rerank_s: float
    bertscore_s: float
    total_s: float


def run_bench(svc, *, sizes: list[int], jd_id: str | None = None, seed: int = 0) -> list[BenchRow]:
    rng = random.Random(seed)
    with svc.connect() as conn:
        cvs = [str(r["cv_id"]) for r in conn.execute(
            "SELECT cv_id FROM cv WHERE is_latest AND status = 'active' AND ontology_version = %s"
            " AND pipeline_version = %s AND embed_model = %s ORDER BY cv_id",
            (svc.cfg.ontology_version, svc.cfg.prep.version, svc.encoder.key()))]
        jds = [r["jd_id"] for r in conn.execute(
            "SELECT DISTINCT jd_id FROM jd WHERE is_latest AND status = 'open' AND ontology_version = %s"
            " AND pipeline_version = %s ORDER BY jd_id", (svc.cfg.ontology_version, svc.cfg.prep.version))]
    if not cvs or not jds:
        raise RuntimeError("DB khong co CV / JD cua bo khoa phien ban dang dung (can reprocess?)")
    jd_id = jd_id or jds[0]
    rows: list[BenchRow] = []
    used: set[str] = set()
    for n in sizes:
        n = min(n, len(cvs))
        fresh = [c for c in cvs if c not in used] or cvs         # pool moi -> gach chua co trong cache RAM
        pool = rng.sample(fresh, min(n, len(fresh))) if len(fresh) >= n else rng.sample(cvs, n)
        used.update(pool)
        for run in ("cold", "warm"):
            t0 = time.perf_counter()
            out = svc.match_jd(jd_id, K=n, N=n, include_cv_ids=pool)
            rows.append(BenchRow("jd_to_cv", n, run, out.timings["retrieve_s"], out.timings["rerank_s"],
                                 out.timings.get("rerank.rr2_b4_bertscore_s", 0.0), time.perf_counter() - t0))
    cv = rng.choice(cvs)
    for run in ("cold", "warm"):
        t0 = time.perf_counter()
        out = svc.match_cv(cv, K=len(jds), N=len(jds))
        rows.append(BenchRow("cv_to_jd", len(jds), run, out.timings["retrieve_s"], out.timings["rerank_s"],
                             out.timings.get("rerank.rr2_b4_bertscore_s", 0.0), time.perf_counter() - t0))
    return rows


def to_markdown(rows: list[BenchRow], *, device: str, threads: int, n_cv: int) -> str:
    out = [f"# Đo thời gian match theo cỡ pool (S05)\n",
           f"- Thiết bị: `{device}`, {threads} luồng torch · kho: {n_cv} CV · rerank toàn bộ pool (K = N = n)",
           "- `cold`: lần đầu với pool đó (cache token BERTScore chỉ ở RAM, chưa có) · `warm`: chạy lại ngay\n",
           "| Luồng | n | Lần | Retrieve (s) | Rerank (s) | trong đó BERTScore (s) | Tổng (s) | ms / ứng viên |",
           "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in rows:
        out.append(f"| {r.flow} | {r.n} | {r.run} | {r.retrieve_s:.3f} | {r.rerank_s:.3f} | {r.bertscore_s:.3f} | "
                   f"{r.total_s:.3f} | {1000 * r.total_s / max(r.n, 1):.1f} |")
    return "\n".join(out) + "\n"
