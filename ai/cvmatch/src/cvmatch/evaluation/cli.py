"""Lenh `cvmatch eval ...`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def cmd_golden(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.core.kb.matcher import SkillMatcher
    from cvmatch.core.kb.snapshot import KBSnapshot
    from cvmatch.core.kb.store import load_snapshot_db
    from cvmatch.core.models import get_encoder
    from cvmatch.evaluation.golden.runner import benchmark, run_golden
    from cvmatch.rerank.bertscore.engine import BertScorer

    ov = {"bertscore": {"canonicalize_aliases": False, "mask_numbers": False}} if args.bare else {}
    cfg = load_config(args.config_dir, overrides=ov)
    if args.kb_dir:
        snap = KBSnapshot.from_dir(args.kb_dir)
    else:
        with connect(args.url) as conn:
            snap = load_snapshot_db(conn, cfg.ontology_version)
    scorer = BertScorer(get_encoder(cfg), cfg.bertscore, SkillMatcher(snap))
    rep = run_golden(scorer, bare=args.bare)
    md = rep.to_markdown()
    if args.bench:
        md += "\n## Chi phí\n\n```json\n" + json.dumps(benchmark(scorer), ensure_ascii=False, indent=2) + "\n```\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(md, encoding="utf-8")
    for s in ("S1", "S2", "S3"):
        p, n = rep.passed(s)
        print(f"{s}: {p}/{n} dat; khong dat: {', '.join(rep.failed_ids(s)) or '-'}")
    if args.bare:
        print("lech lon nhat so voi file 10: %.4f (%s)" % rep.max_diff_vs_doc())
    p, n = rep.passed("S2")
    return 0 if p >= 25 else 1   # G1: giu cau hinh khi S2 dat >= 25/26


def register(sub: argparse._SubParsersAction) -> None:
    ev = sub.add_parser("eval", help="danh gia va thi nghiem")
    evs = ev.add_subparsers(dest="cmd", required=True)
    g = evs.add_parser("golden", help="golden test BERTScore T01-T24, F01-F05 (G1/G2)")
    g.add_argument("--bare", action="store_true", help="mo hinh tran: tat doi alias va che so")
    g.add_argument("--bench", action="store_true", help="kem do chi phi 200 CV x 8 gach x 3 trach nhiem")
    g.add_argument("--out", default=None, help="ghi bao cao Markdown")
    g.add_argument("--kb-dir", default=None)
    g.add_argument("--config-dir", default=None)
    g.add_argument("--url", default=None)
    g.set_defaults(func=cmd_golden)
