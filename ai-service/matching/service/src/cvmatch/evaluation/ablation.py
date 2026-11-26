"""Runner ablation theo "ke hoach thi nghiem" YAML (thiet ke 09 muc 3.2, 3.3, 4.3, 4.5).

Moi cau hinh la mot PHAN GHI DE len config dang dung (`load_config(overrides=...)`) - chay thi nghiem chi
bang doi file, khong sua code. Chay Retrieve (va Rerank) tren tap truy van (dev) cua mot DB da nap san
CV/JD, KHONG ghi log match_run / rerank_run.

Ke hoach:

    name: R-ablation
    direction: jd_to_cv            # jd_to_cv (Luong C) | cv_to_jd (Luong D)
    stage: rerank                  # retrieve: Recall@K ; rerank: nDCG@10, Recall@N
    reference: P1                  # cau hinh moc de bootstrap chenh lech
    relevant_min_grade: 1          # "phu hop" = nhan >= 1 hay = 2 (chot TRUOC khi cham)
    K: 200
    N: 30
    recall_ks: [50, 100, 200, 300]
    base: {}                       # ghi de chung cho moi cau hinh
    configs:
      - {id: R-A0, mode: retrieve_only, desc: top N theo fused}
      - {id: P1, overrides: {}}
      - {id: R-E3, todo: "engine rerank chua co S1/S3"}   # chua chay duoc -> ghi vao bao cao
    grid:                          # (tuy chon) sinh cau hinh luoi trong so (R-E13)
      id_prefix: R-E13
      base_overrides: {...}
      groups: {A: [A1, A2], B45: [B4, B5], B13: [B1, B2, B3], C: [C1]}
      multipliers: [0, 0.5, 1, 1.5]

Ket qua: bang Markdown + CSV theo truy van + bieu do SVG chi phi - chat luong (thoi gian/truy van vs chi so chinh).
"""

from __future__ import annotations

import csv
import itertools
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from cvmatch.core.config import AppConfig, _deep_merge, load_config
from cvmatch.core.db import connect
from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.kb.store import load_snapshot_db
from cvmatch.evaluation import metrics as M
from cvmatch.evaluation.bootstrap import paired_bootstrap
from cvmatch.evaluation.labels import GradedLabels
from cvmatch.rerank.bertscore.cache import TokenCache
from cvmatch.rerank.bertscore.engine import BertScorer
from cvmatch.rerank.run import Reranker


# --------------------------------------------------------------------------- ke hoach


@dataclass
class ExpConfig:
    id: str
    desc: str = ""
    overrides: dict = field(default_factory=dict)
    mode: str = "full"              # full | retrieve_only (R-A0)
    todo: str | None = None


@dataclass
class Plan:
    name: str
    direction: str = "jd_to_cv"
    stage: str = "rerank"
    reference: str | None = None
    relevant_min_grade: int = 1
    K: int | None = None
    N: int | None = None
    recall_ks: list[int] = field(default_factory=lambda: [50, 100, 200, 300])
    base: dict = field(default_factory=dict)
    configs: list[ExpConfig] = field(default_factory=list)
    main: str | None = None          # chi so chinh (mac dinh: ndcg@10 | recall@200 | recall@max(recall_ks))

    @property
    def main_metric(self) -> str:
        if self.main:
            return self.main
        if self.stage == "rerank":
            return "ndcg@10"
        return "recall@200" if 200 in self.recall_ks else f"recall@{max(self.recall_ks)}"


def _grid(spec: dict, prior: dict[str, float]) -> list[ExpConfig]:
    groups: dict[str, list[str]] = spec["groups"]
    mults = spec.get("multipliers", [0, 0.5, 1, 1.5])
    out = []
    for combo in itertools.product(mults, repeat=len(groups)):
        w = {f: prior.get(f, 0.0) * m for (g, fs), m in zip(groups.items(), combo) for f in fs}
        total = sum(w.values())
        if total <= 0:
            continue
        w = {f: v / total for f, v in w.items()}
        w = {f: w.get(f, 0.0) for f in prior}
        drift = 1.0 - sum(w.values())                   # lam tron de tong dung 1,00
        k = max(w, key=w.get)
        w[k] += drift
        tag = "-".join(f"{g}{m:g}" for g, m in zip(groups, combo))
        ov = _deep_merge(spec.get("base_overrides", {}), {"rerank": {"weights": w}})
        out.append(ExpConfig(id=f"{spec.get('id_prefix', 'grid')}:{tag}", desc="luoi trong so", overrides=ov))
    return out


def load_plan(path: str | Path, *, prior_weights: dict[str, float] | None = None) -> Plan:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cfgs = [ExpConfig(id=c["id"], desc=c.get("desc", ""), overrides=c.get("overrides") or {},
                      mode=c.get("mode", "full"), todo=c.get("todo")) for c in d.get("configs") or []]
    if d.get("grid"):
        prior = prior_weights or dict(load_config().rerank.weights)
        cfgs += _grid(d["grid"], prior)
    return Plan(name=d.get("name", Path(path).stem), direction=d.get("direction", "jd_to_cv"),
                stage=d.get("stage", "rerank"), reference=d.get("reference"),
                relevant_min_grade=int(d.get("relevant_min_grade", 1)), K=d.get("K"), N=d.get("N"),
                recall_ks=list(d.get("recall_ks") or [50, 100, 200, 300]), base=d.get("base") or {}, configs=cfgs,
                main=d.get("main_metric"))


# --------------------------------------------------------------------------- chay


@dataclass
class ConfigResult:
    id: str
    desc: str
    per_query: dict[str, dict[str, float | None]]       # metric -> {query: gia tri}
    summary: dict[str, dict]
    time_ms: dict[str, float]                           # mean, p95 (moi truy van)
    unjudged: float | None
    todo: str | None = None
    error: str | None = None
    config_hash: str | None = None


@dataclass
class AblationReport:
    plan: Plan
    results: list[ConfigResult]
    bootstrap: dict[str, dict | None]
    queries: list[str]

    def result(self, cid: str) -> ConfigResult:
        return next(r for r in self.results if r.id == cid)


class _Cache:
    def __init__(self, conn, encoder):
        self.conn, self.encoder = conn, encoder
        self.snap: dict = {}
        self.index: dict = {}
        self.jd_index: dict = {}
        self.scorer: dict = {}

    def snapshot(self, cfg: AppConfig):
        v = cfg.ontology_version
        if v not in self.snap:
            self.snap[v] = load_snapshot_db(self.conn, v)
        return self.snap[v]

    def cv_index(self, cfg: AppConfig):
        from cvmatch.retrieve.index import CvIndex

        key = json.dumps([cfg.retrieve.bm25.model_dump(), cfg.versions.model_dump()], sort_keys=True)
        if key not in self.index:
            self.index[key] = CvIndex(cfg).build(self.conn)
        return self.index[key]

    def jd_idx(self, cfg: AppConfig):
        from cvmatch.retrieve.jd_index import JdIndex

        key = json.dumps([cfg.retrieve.bm25.model_dump(), cfg.versions.model_dump()], sort_keys=True)
        if key not in self.jd_index:
            self.jd_index[key] = JdIndex(cfg).build(self.conn)
        return self.jd_index[key]

    def bert(self, cfg: AppConfig) -> BertScorer:
        key = cfg.bertscore.key()
        if key not in self.scorer:
            self.scorer[key] = BertScorer(self.encoder, cfg.bertscore, SkillMatcher(self.snapshot(cfg)), TokenCache(key))
        return self.scorer[key]


def _query_metrics(plan: Plan, ranked: list[str], pool: list[str], labels: dict[str, int], N: int) -> dict:
    g = plan.relevant_min_grade
    if plan.stage == "retrieve":
        out = {f"recall@{k}": M.recall_at_k(ranked, labels, k, min_grade=g) for k in plan.recall_ks}
        out["unjudged"] = M.unjudged_rate(ranked, labels, max(plan.recall_ks))
        return out
    return {"ndcg@10": M.ndcg_at_k(ranked, labels, 10, universe=pool),
            f"recall@{N}": M.recall_at_k(ranked, labels, N, min_grade=g, universe=pool),
            f"recall@{N}_norm": M.recall_at_k_norm(ranked, labels, N, min_grade=g, universe=pool),
            "unjudged": M.unjudged_rate(ranked, labels, 10)}


def _run_one(plan: Plan, c: ExpConfig, cache: _Cache, queries: list[str], labels: GradedLabels, *,
             config_dir, extra_overrides: dict, ref_ym: str | None, groups: dict) -> ConfigResult:
    from cvmatch.retrieve.jd_to_cvs import retrieve_for_jd

    ov = _deep_merge(_deep_merge(plan.base, c.overrides), extra_overrides)
    cfg = load_config(config_dir, overrides=ov)
    conn = cache.conn
    reverse = plan.direction == "cv_to_jd"
    N = plan.N or (cfg.rerank.reverse_N if reverse else cfg.rerank.N)
    rr = None
    if plan.stage == "rerank" and c.mode != "retrieve_only":
        rr = Reranker(cfg, cache.bert(cfg), cache.snapshot(cfg))
    idx = cache.jd_idx(cfg) if reverse else cache.cv_index(cfg)
    per: dict[str, dict[str, float | None]] = {}
    times = []
    for q in queries:
        t0 = time.perf_counter()
        if reverse:
            from cvmatch.retrieve.cv_to_jds import retrieve_for_cv

            res = retrieve_for_cv(conn, idx, cfg, q, K=plan.K, write_log=False)
            ids = [it["jd_id"] for it in res.items]
        else:
            res = retrieve_for_jd(conn, idx, cfg, q, K=plan.K, write_log=False)
            ids = [it["cv_id"] for it in res.items]
        ranked = ids
        if rr is not None:
            req = res.request.model_copy(update={"N": len(res.request.candidates)})
            out = rr.rerank(conn, req, ref_ym=ref_ym, write=False)
            ranked = [r.cv_id for r in out.rows]
        times.append((time.perf_counter() - t0) * 1000)
        for k, v in _query_metrics(plan, ranked, ids, labels.for_query(q), N).items():
            per.setdefault(k, {})[q] = v
    summ = {k: M.summarize(v, groups) for k, v in per.items() if k != "unjudged"}
    unj = [v for v in per.get("unjudged", {}).values() if v is not None]
    return ConfigResult(c.id, c.desc, per, summ,
                        {"mean": float(np.mean(times)) if times else 0.0,
                         "p95": float(np.percentile(times, 95)) if times else 0.0},
                        float(np.mean(unj)) if unj else None, config_hash=cfg.config_hash())


def run_ablation(plan: Plan, labels: GradedLabels, *, url: str | None = None, encoder=None,
                 queries: list[str] | None = None, config_dir=None, extra_overrides: dict | None = None,
                 ref_ym: str | None = None, groups: dict[str, str] | None = None,
                 only: list[str] | None = None) -> AblationReport:
    from cvmatch.core.models import get_encoder

    queries = sorted(queries if queries is not None else labels.queries)
    with connect(url) as conn:
        cfg0 = load_config(config_dir, overrides=_deep_merge(plan.base, extra_overrides or {}))
        cache = _Cache(conn, encoder or get_encoder(cfg0))
        results = []
        for c in plan.configs:
            if only and c.id not in only:
                continue
            if c.todo:
                results.append(ConfigResult(c.id, c.desc, {}, {}, {}, None, todo=c.todo))
                continue
            try:
                results.append(_run_one(plan, c, cache, queries, labels, config_dir=config_dir,
                                        extra_overrides=extra_overrides or {}, ref_ym=ref_ym, groups=groups or {}))
            except Exception as e:  # noqa: BLE001 - cau hinh loi khong lam hong ca ke hoach
                results.append(ConfigResult(c.id, c.desc, {}, {}, {}, None, error=f"{type(e).__name__}: {e}"))
    ref = plan.reference or next((r.id for r in results if r.per_query), None)
    boot: dict[str, dict | None] = {}
    ref_r = next((r for r in results if r.id == ref and r.per_query), None)
    for r in results:
        if ref_r is None or not r.per_query or r.id == ref:
            continue
        b = paired_bootstrap(ref_r.per_query.get(plan.main_metric, {}), r.per_query.get(plan.main_metric, {}))
        boot[r.id] = None if b is None else {"diff": b.diff, "lo": b.lo, "hi": b.hi, "n": b.n,
                                             "significant": b.significant}
    plan.reference = ref
    return AblationReport(plan, results, boot, queries)


# --------------------------------------------------------------------------- bao cao


def _f(x, p=3):
    return "–" if x is None else f"{x:.{p}f}"


def to_markdown(rep: AblationReport) -> str:
    p = rep.plan
    mm = p.main_metric
    def _order(k):
        num = k.split("@")[-1].split("_")[0]
        return (k != mm, k.split("@")[0], int(num) if num.isdigit() else 0, k)

    metrics = sorted({k for r in rep.results for k in r.summary}, key=_order)
    out = [f"# Ablation `{p.name}` ({p.direction}, {p.stage})", "",
           f"- {len(rep.queries)} truy vấn · chỉ số chính **{mm}** · phù hợp = nhãn ≥ {p.relevant_min_grade}"
           f" · mốc bootstrap: `{p.reference}` (CI 95%, ghép cặp theo truy vấn)", "",
           "| Cấu hình | Mô tả | " + " | ".join(metrics) + " | Δ vs mốc [CI 95%] | tệ nhất | ms/truy vấn | chưa chấm |",
           "| --- | --- | " + " | ".join("---" for _ in metrics) + " | --- | --- | --- | --- |"]
    for r in rep.results:
        if r.todo or r.error:
            out.append(f"| {r.id} | {r.desc} | " + " | ".join("–" for _ in metrics) +
                       f" | {'todo: ' + r.todo if r.todo else 'lỗi: ' + r.error} | – | – | – |")
            continue
        b = rep.bootstrap.get(r.id)
        bs = "mốc" if r.id == p.reference else ("–" if b is None else
                                               f"{b['diff']:+.3f} [{b['lo']:+.3f}; {b['hi']:+.3f}]{' *' if b['significant'] else ''}")
        worst = r.summary.get(mm, {})
        out.append(f"| {r.id} | {r.desc} | " + " | ".join(_f(r.summary.get(k, {}).get('mean')) for k in metrics) +
                   f" | {bs} | {_f(worst.get('worst'))} ({worst.get('worst_query') or '–'}) | {r.time_ms.get('mean', 0):.0f}"
                   f" | {_f(r.unjudged, 2)} |")
    groups = sorted({g for r in rep.results for g in r.summary.get(mm, {}).get("by_group", {})})
    if groups:
        out += ["", f"## {mm} theo nhóm", "", "| Cấu hình | " + " | ".join(groups) + " |",
                "| --- | " + " | ".join("---" for _ in groups) + " |"]
        for r in rep.results:
            bg = r.summary.get(mm, {}).get("by_group", {})
            if bg:
                out.append(f"| {r.id} | " + " | ".join(_f(bg.get(g)) for g in groups) + " |")
    out += ["", "`*`: khoảng tin cậy không chứa 0. Chênh nhỏ hơn khoảng tin cậy là nhiễu (thiết kế 09 mục 4.5).",
            "Quy tắc chọn: cấu hình đơn giản nhất có chỉ số chính kém tốt nhất ≤ 1–2 điểm; thành phần chỉ giữ khi"
            " cải thiện vượt ngưỡng đặt trước.", "", "Biểu đồ chi phí – chất lượng: `cost_quality.svg`."]
    return "\n".join(out) + "\n"


def cost_quality_svg(rep: AblationReport, width: int = 640, height: int = 420) -> str:
    """SVG tinh (khong phu thuoc thu vien ve): x = ms/truy van, y = chi so chinh; danh dau bien Pareto."""
    mm = rep.plan.main_metric
    pts = [(r.id, r.time_ms["mean"], r.summary[mm]["mean"]) for r in rep.results
           if r.per_query and r.summary.get(mm, {}).get("mean") is not None]
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 50
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    if not pts:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"></svg>'
    xs, ys = [p[1] for p in pts], [p[2] for p in pts]
    x0, x1 = 0.0, max(xs) * 1.1 or 1.0
    y0, y1 = max(0.0, min(ys) - 0.05), min(1.0, max(ys) + 0.05)
    if y1 - y0 < 1e-6:
        y0, y1 = y0 - 0.05, y1 + 0.05
    sx = lambda x: pad_l + (x - x0) / (x1 - x0) * W  # noqa: E731
    sy = lambda y: pad_t + (1 - (y - y0) / (y1 - y0)) * H  # noqa: E731
    pareto = {pid for pid, x, y in pts if not any((x2 <= x and y2 >= y) and (x2 < x or y2 > y) for _, x2, y2 in pts)}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif" font-size="11">',
         f'<rect width="{width}" height="{height}" fill="white"/>',
         f'<line x1="{pad_l}" y1="{pad_t + H}" x2="{pad_l + W}" y2="{pad_t + H}" stroke="#333"/>',
         f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + H}" stroke="#333"/>',
         f'<text x="{pad_l + W / 2}" y="{height - 12}" text-anchor="middle">ms / truy vấn</text>',
         f'<text x="14" y="{pad_t + H / 2}" transform="rotate(-90 14 {pad_t + H / 2})" text-anchor="middle">{mm}</text>',
         f'<text x="{pad_l}" y="18">Chi phí – chất lượng ({rep.plan.name})</text>']
    for t in range(5):
        yv = y0 + (y1 - y0) * t / 4
        xv = x0 + (x1 - x0) * t / 4
        s.append(f'<text x="{pad_l - 6}" y="{sy(yv) + 4}" text-anchor="end">{yv:.2f}</text>')
        s.append(f'<text x="{sx(xv)}" y="{pad_t + H + 16}" text-anchor="middle">{xv:.0f}</text>')
    for pid, x, y in pts:
        col = "#c0392b" if pid in pareto else "#2c6fbb"
        s.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="{col}"/>')
        s.append(f'<text x="{sx(x) + 6:.1f}" y="{sy(y) - 6:.1f}">{pid}</text>')
    s.append(f'<text x="{pad_l + W - 4}" y="{pad_t + 12}" text-anchor="end" fill="#c0392b">đỏ = biên Pareto</text>')
    s.append("</svg>")
    return "\n".join(s)


def write_report(rep: AblationReport, out_dir: str | Path) -> Path:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "ablation.md").write_text(to_markdown(rep), encoding="utf-8")
    (d / "cost_quality.svg").write_text(cost_quality_svg(rep), encoding="utf-8")
    with (d / "per_query.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config", "metric", "query_id", "value"])
        for r in rep.results:
            for m, vals in r.per_query.items():
                for q, v in sorted(vals.items()):
                    w.writerow([r.id, m, q, "" if v is None else f"{v:.6f}"])
    (d / "summary.json").write_text(json.dumps(
        {"plan": rep.plan.name, "reference": rep.plan.reference, "queries": rep.queries,
         "results": [{"id": r.id, "summary": r.summary, "time_ms": r.time_ms, "unjudged": r.unjudged, "todo": r.todo,
                      "error": r.error, "config_hash": r.config_hash} for r in rep.results],
         "bootstrap": rep.bootstrap}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return d
