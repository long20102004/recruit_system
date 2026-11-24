"""Lenh `cvmatch demo generate|seed|serve|scenarios` (moi truong thu API nhu that)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def cmd_generate(args: argparse.Namespace) -> int:
    from cvmatch.demo.generate import generate

    print(generate(args.data_dir, n_cv=args.n_cv, seed=args.seed))
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    from cvmatch.demo.seed import seed

    if args.url:
        os.environ["CVMATCH_DB_URL"] = args.url
    seed(data_dir=args.data_dir, db_name=args.db, kb_dir=args.kb_dir, n_cv=args.n_cv, fake=args.fake_encoder,
         reset=args.reset, regenerate=args.regenerate, batch=args.batch, data_seed=args.seed)
    print(f"\nTiep theo: python -m cvmatch.cli demo serve   (roi)   python -m cvmatch.cli demo scenarios")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from cvmatch.api.app import create_app
    from cvmatch.demo.seed import load_state, services_from_state

    state = load_state(Path(args.data_dir) / "state.json")
    print(f"API demo: DB {state['db_name']} · KB {state['kb_version']} · "
          f"{'FakeEncoder' if state['fake_encoder'] else 'bge-m3'} · http://{args.host}:{args.port}/docs")
    uvicorn.run(create_app(lambda: services_from_state(state)), host=args.host, port=args.port, log_level="info")
    return 0


def cmd_scenarios(args: argparse.Namespace) -> int:
    from cvmatch.demo.scenarios import run_all, to_markdown, write_report
    from cvmatch.demo.seed import load_state

    state = load_state(Path(args.data_dir) / "state.json")
    results, lat = run_all(args.api, state, only=args.only.split(",") if args.only else None)
    md = to_markdown(results, lat, args.api, state)
    write_report(args.out, md)
    print(f"\n{sum(r.ok for r in results)}/{len(results)} dat -> {args.out}")
    return 0 if all(r.ok for r in results) else 1


def cmd_postman(args: argparse.Namespace) -> int:
    from cvmatch.demo.postman import write
    from cvmatch.demo.seed import load_state

    state = load_state(Path(args.data_dir) / "state.json")
    for p in write(state, args.out or Path(args.data_dir) / "postman", args.api):
        print("->", p)
    print("Postman: Import 2 file tren, chon environment 'cvmatch demo', chay thu muc 0 -> 6 (hoac Run collection).")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from cvmatch.demo.inspect import Demo
    from cvmatch.demo.seed import load_state

    print(Demo(load_state(Path(args.data_dir) / "state.json")).show(args.key))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    from cvmatch.demo.inspect import inspect_run
    from cvmatch.demo.seed import load_state

    md = inspect_run(load_state(Path(args.data_dir) / "state.json"), args.run_id, show_all=args.all)
    out = Path(args.out or f"reports/demo/inspect_{args.run_id[:8]}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"-> {out}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    from cvmatch.demo.seed import DEFAULT_DIR, DEFAULT_KB

    d = sub.add_parser("demo", help="moi truong thu API nhu that: DB demo + vai tram CV/JD da nap")
    ds = d.add_subparsers(dest="cmd", required=True)

    g = ds.add_parser("generate", help="chi sinh du lieu CV/JD tong hop vao data/demo/")
    g.add_argument("--n-cv", type=int, default=300)
    g.add_argument("--seed", type=int, default=2026)
    g.add_argument("--data-dir", default=str(DEFAULT_DIR))
    g.set_defaults(func=cmd_generate)

    s = ds.add_parser("seed", help="sinh du lieu (neu chua co) + tao DB + nap KB + nap CV/JD qua Luong A/B")
    s.add_argument("--db", default="cvmatch_demo", help="ten database (tao tren server cua CVMATCH_DB_URL)")
    s.add_argument("--n-cv", type=int, default=300)
    s.add_argument("--seed", type=int, default=2026)
    s.add_argument("--kb-dir", default=str(DEFAULT_KB))
    s.add_argument("--batch", type=int, default=32)
    s.add_argument("--fake-encoder", action="store_true", help="khong GPU (diem khong co nghia ngu nghia)")
    s.add_argument("--reset", action="store_true", help="xoa DB demo cu va nap lai tu dau")
    s.add_argument("--regenerate", action="store_true", help="sinh lai du lieu (doi --n-cv / --seed)")
    s.add_argument("--data-dir", default=str(DEFAULT_DIR))
    s.add_argument("--url", default=None, help="URL server Postgres (mac dinh CVMATCH_DB_URL)")
    s.set_defaults(func=cmd_seed)

    v = ds.add_parser("serve", help="chay API tren DB demo (doc data/demo/state.json)")
    v.add_argument("--host", default="127.0.0.1")
    v.add_argument("--port", type=int, default=8090)
    v.add_argument("--data-dir", default=str(DEFAULT_DIR))
    v.set_defaults(func=cmd_serve)

    c = ds.add_parser("scenarios", help="chay bo kich ban HTTP vao API dang chay")
    c.add_argument("--api", default="http://127.0.0.1:8090")
    c.add_argument("--only", default=None, help="vd health,match_params")
    c.add_argument("--data-dir", default=str(DEFAULT_DIR))
    c.add_argument("--out", default="reports/demo/scenarios.md")
    c.set_defaults(func=cmd_scenarios)

    pm = ds.add_parser("postman", help="sinh Postman collection + environment dung cv_id / jd_id that cua DB demo")
    pm.add_argument("--api", default="http://127.0.0.1:8090")
    pm.add_argument("--data-dir", default=str(DEFAULT_DIR))
    pm.add_argument("--out", default=None, help="mac dinh data/demo/postman/")
    pm.set_defaults(func=cmd_postman)

    sh = ds.add_parser("show", help="JSON goc + thong tin that (vai tro, cap, so nam) cua mot CV / JD demo")
    sh.add_argument("key", help="cv_id, jd_id (vd DEMO-003) hoac ten file (vd cv_0002_java.json)")
    sh.add_argument("--data-dir", default=str(DEFAULT_DIR))
    sh.set_defaults(func=cmd_show)

    ins = ds.add_parser("inspect", help="doi chieu top N cua mot lan match (run_id tu API) voi du lieu goc")
    ins.add_argument("run_id")
    ins.add_argument("--all", action="store_true", help="in ca pool rerank, khong chi top N")
    ins.add_argument("--data-dir", default=str(DEFAULT_DIR))
    ins.add_argument("--out", default=None)
    ins.set_defaults(func=cmd_inspect)
