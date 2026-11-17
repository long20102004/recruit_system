"""Lenh `cvmatch rerank <retrieve_run_id> [--n 30]`."""

from __future__ import annotations

import argparse


def build_reranker(conn, cfg, *, db_cache: bool = True):
    from cvmatch.core.kb.matcher import SkillMatcher
    from cvmatch.core.kb.store import load_snapshot_db
    from cvmatch.core.models import get_encoder
    from cvmatch.rerank.bertscore.cache import TokenCache
    from cvmatch.rerank.bertscore.engine import BertScorer
    from cvmatch.rerank.run import Reranker

    snap = load_snapshot_db(conn, cfg.ontology_version)
    cache = TokenCache(cfg.bertscore.key(), conn=conn if db_cache else None)
    scorer = BertScorer(get_encoder(cfg), cfg.bertscore, SkillMatcher(snap), cache)
    return Reranker(cfg, scorer, snap)


def cmd_rerank(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.rerank.run import request_from_run

    cfg = load_config(args.config_dir)
    with connect(args.url) as conn:
        rr = build_reranker(conn, cfg, db_cache=not args.no_db_cache)
        req = request_from_run(conn, cfg, args.retrieve_run_id, N=args.n)
        out = rr.rerank(conn, req, ref_ym=args.ref_ym)
    t = out.timings
    print(f"rerank run {out.run_id} · {len(out.rows)} CV -> top {len(out.items)} · tong {t['total_s']:.2f}s"
          f" (BERTScore {t.get('rr2_bertscore_s', 0):.2f}s)")
    for w in out.warnings:
        print("  canh bao:", w["message"])
    fmt = lambda x: "    -" if x is None else f"{x:.3f}"  # noqa: E731
    print(f"{'hang':>4} {'diem':>4} {'S_raw':>6} {'cap':>4} {'A1':>6} {'B4':>6} {'B1':>6} {'B2':>6}  cv_id  co")
    for it in out.items[: args.top]:
        f = it.features
        print(f"{it.rank:>4} {it.score:>4} {it.score_raw:.3f} {it.gate_cap:>4} {fmt(f.A1):>6} {fmt(f.B4):>6}"
              f" {fmt(f.B1):>6} {fmt(f.B2):>6}  {it.cv_id}  {','.join(it.flags) or '-'}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    r = sub.add_parser("rerank", help="Tang 2 Rerank cho mot retrieve run (chieu JD -> CV)")
    r.add_argument("retrieve_run_id")
    r.add_argument("--n", type=int, default=None, help="so CV giu lai (mac dinh rerank.N)")
    r.add_argument("--top", type=int, default=30, help="so dong in ra")
    r.add_argument("--ref-ym", default=None, help="thang tham chieu cho B1 (mac dinh thang hien tai)")
    r.add_argument("--no-db-cache", action="store_true", help="chi cache token trong RAM")
    r.add_argument("--config-dir", default=None)
    r.add_argument("--url", default=None)
    r.set_defaults(func=cmd_rerank)
