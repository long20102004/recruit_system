"""Lenh `cvmatch explain <rerank_run_id> <cv_id> [--json] [--force]`."""

from __future__ import annotations

import argparse
import json


def cmd_explain(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.core.kb.store import load_snapshot_db
    from cvmatch.explain.service import ExplainService

    cfg = load_config(args.config_dir)
    with connect(args.url) as conn:
        svc = ExplainService(cfg, load_snapshot_db(conn, cfg.ontology_version))
        out = svc.explain(conn, args.run_id, args.cv_id, force=args.force)
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else out["text"])
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    e = sub.add_parser("explain", help="Tang 3 Explain: giai thich mot CV trong mot rerank run")
    e.add_argument("run_id")
    e.add_argument("cv_id")
    e.add_argument("--json", action="store_true", help="in explanation_json (co cau truc)")
    e.add_argument("--force", action="store_true", help="bo qua cache")
    e.add_argument("--config-dir", default=None)
    e.add_argument("--url", default=None)
    e.set_defaults(func=cmd_explain)
