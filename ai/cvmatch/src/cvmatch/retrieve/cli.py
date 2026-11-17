"""Lenh `cvmatch retrieve ...` (dung chi muc RAM moi lan goi - dich vu that giu chi muc trong T13)."""

from __future__ import annotations

import argparse
import time


def cmd_retrieve_jd(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.retrieve.flow_c import retrieve_for_jd
    from cvmatch.retrieve.index import CvIndex

    cfg = load_config(args.config_dir)
    with connect(args.url) as conn:
        t = time.perf_counter()
        idx = CvIndex(cfg).build(conn)
        tb = time.perf_counter() - t
        t = time.perf_counter()
        res = retrieve_for_jd(conn, idx, cfg, args.jd_id, K=args.k,
                              views=args.views.split(",") if args.views else None)
        tr = time.perf_counter() - t
    print(f"run_id {res.run_id} · JD {res.jd_id} v{res.jd_version} · pool {res.n_pool} CV · views {res.views_used}"
          f" · dung chi muc {tb:.1f}s · cham {tr * 1000:.0f} ms")
    for w in res.warnings:
        print("  canh bao:", w["message"])
    print(f"{'hang':>4} {'fused':>6} {'dense':>6} {'bm25':>7} {'skill':>6} {'resp':>6}  cv_id")
    fmt = lambda x, p=3: "    -" if x is None else f"{x:.{p}f}"  # noqa: E731
    for it in res.items[: args.top]:
        s = it["s"]
        print(f"{it['rank']:>4} {it['fused']:.3f} {fmt(s['dense']):>6} {fmt(s['bm25'], 2):>7} {fmt(s['skill']):>6}"
              f" {fmt(s['resp']):>6}  {it['cv_id']}  thieu: {', '.join(it['explanation']['skills_missing']) or '-'}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.retrieve.index import CvIndex

    cfg = load_config(args.config_dir)
    with connect(args.url) as conn:
        idx = CvIndex(cfg).build(conn)
        issues = idx.verify(conn)
    print(f"{idx.n_cv} CV, {len(idx.bullet_ids)} gach, RAM {idx.memory_mb()}")
    print("khop Postgres" if not issues else "\n".join(issues))
    return 0 if not issues else 1


def register(sub: argparse._SubParsersAction) -> None:
    r = sub.add_parser("retrieve", help="Tang 1 Retrieve")
    rs = r.add_subparsers(dest="cmd", required=True)
    j = rs.add_parser("jd", help="Luong C: JD -> top K CV")
    j.add_argument("jd_id")
    j.add_argument("--k", type=int, default=None)
    j.add_argument("--views", default=None, help="vd dense,bm25,skill")
    j.add_argument("--top", type=int, default=20)
    j.add_argument("--config-dir", default=None)
    j.add_argument("--url", default=None)
    j.set_defaults(func=cmd_retrieve_jd)
    v = rs.add_parser("verify", help="dung chi muc va so voi Postgres")
    v.add_argument("--config-dir", default=None)
    v.add_argument("--url", default=None)
    v.set_defaults(func=cmd_verify)
