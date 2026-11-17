"""Diem vao dong lenh `cvmatch`. Moi package dang ky lenh con cua minh o day."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_db_migrate(args: argparse.Namespace) -> int:
    from cvmatch.core.db import migrate

    ran = migrate(args.url)
    print("Da chay:", ", ".join(ran) if ran else "(khong co migration moi)")
    return 0


def _cmd_db_status(args: argparse.Namespace) -> int:
    from cvmatch.core.db import applied_migrations, connect, list_tables

    with connect(args.url, autocommit=True) as conn:
        print("Migrations:", ", ".join(sorted(applied_migrations(conn))) or "(chua co)")
        tables = list_tables(conn)
        print(f"{len(tables)} bang:", ", ".join(tables))
    return 0


def _cmd_config_show(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config

    cfg = load_config(args.config_dir)
    print(json.dumps(cfg.versions.model_dump(), ensure_ascii=False, indent=2))
    print("config_hash:", cfg.config_hash())
    return 0


def _cmd_kb_import(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.core.kb.store import import_snapshot, load_snapshot_db

    with connect(args.url) as conn:
        version = import_snapshot(conn, args.path, replace=args.replace)
        snap = load_snapshot_db(conn, version)
    print(f"Da nap {version}: {len(snap.skills)} ky nang, {len(snap.title_map)} alias chuc danh, "
          f"{len(snap.level_map)} alias cap bac, {len(snap.major_map)} alias nganh, {len(snap.ambiguous)} alias de nham")
    print(f"Dat `ontology_version: {version}` trong config/active.yaml de dung mac dinh.")
    return 0


def _cmd_kb_list(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.core.kb.store import list_versions

    with connect(args.url) as conn:
        for r in list_versions(conn):
            print(r["ontology_version"], r["imported_at"], "dev" if r["include_candidate"] else "")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cvmatch")
    sub = p.add_subparsers(dest="group", required=True)

    db = sub.add_parser("db", help="quan ly schema PostgreSQL")
    dbs = db.add_subparsers(dest="cmd", required=True)
    m = dbs.add_parser("migrate", help="chay cac migration chua chay")
    m.add_argument("--url", default=None)
    m.set_defaults(func=_cmd_db_migrate)
    s = dbs.add_parser("status", help="liet ke migration va bang")
    s.add_argument("--url", default=None)
    s.set_defaults(func=_cmd_db_status)

    cfg = sub.add_parser("config", help="cau hinh co phien ban")
    cfgs = cfg.add_subparsers(dest="cmd", required=True)
    sh = cfgs.add_parser("show", help="in bo khoa phien ban va config_hash")
    sh.add_argument("--config-dir", default=None)
    sh.set_defaults(func=_cmd_config_show)

    kb = sub.add_parser("kb", help="ban chup Knowledge Base")
    kbs = kb.add_subparsers(dest="cmd", required=True)
    ki = kbs.add_parser("import", help="nap thu muc snapshot (build_kb/out/snapshot/<version>) vao Postgres")
    ki.add_argument("path")
    ki.add_argument("--replace", action="store_true", help="ghi de ban -dev da nap")
    ki.add_argument("--url", default=None)
    ki.set_defaults(func=_cmd_kb_import)
    kl = kbs.add_parser("list", help="cac ban chup da nap")
    kl.add_argument("--url", default=None)
    kl.set_defaults(func=_cmd_kb_list)

    from cvmatch.ingest import cli as ingest_cli

    ingest_cli.register(sub)

    from cvmatch.retrieve import cli as retrieve_cli

    retrieve_cli.register(sub)

    from cvmatch.rerank import cli as rerank_cli

    rerank_cli.register(sub)

    from cvmatch.explain import cli as explain_cli

    explain_cli.register(sub)

    from cvmatch.evaluation import cli as eval_cli

    eval_cli.register(sub)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
