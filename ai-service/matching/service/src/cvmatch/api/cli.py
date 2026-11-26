"""Lenh `cvmatch api serve` va `cvmatch run-e2e`."""

from __future__ import annotations

import argparse
import json
import os


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from cvmatch.api.app import create_app
    from cvmatch.api.services import Services, config_and_encoder

    if args.url:
        os.environ["CVMATCH_DB_URL"] = args.url

    def factory() -> Services:
        cfg, enc = config_and_encoder(args.config_dir, fake=True if args.fake_encoder else None)
        return Services(cfg, encoder=enc)

    uvicorn.run(create_app(factory), host=args.host, port=args.port, log_level="info")
    return 0


def cmd_prod(args: argparse.Namespace) -> int:
    """Container: cho DB -> migrate -> nap KB (neu chua) -> API tren 0.0.0.0. Cau hinh hoan toan bang env."""
    import uvicorn

    if os.environ.get("CVMATCH_ENV", "dev") == "prod" and not os.environ.get("CVMATCH_SERVICE_TOKEN"):
        print("cvmatch bootstrap loi: CVMATCH_ENV=prod can CVMATCH_SERVICE_TOKEN", flush=True)
        return 2

    from cvmatch.api.app import create_app
    from cvmatch.api.bootstrap import BootstrapError, bootstrap
    from cvmatch.api.logjson import setup_json_logging
    from cvmatch.api.services import Services, config_and_encoder
    from cvmatch.core.config import load_config
    from cvmatch.core.db import db_url

    setup_json_logging(stream=True)
    url = db_url()
    try:
        bootstrap(url, load_config(), kb_dir=os.environ.get("CVMATCH_KB_DIR"),
                  db_timeout_s=float(os.environ.get("CVMATCH_DB_WAIT_S", "120")))
    except BootstrapError as e:
        print(f"cvmatch bootstrap loi: {e}", flush=True)
        return 2

    def factory() -> Services:
        cfg, enc = config_and_encoder()
        return Services(cfg, url=url, encoder=enc)

    uvicorn.run(create_app(factory), host=os.environ.get("CVMATCH_HOST", "0.0.0.0"),
                port=int(os.environ.get("CVMATCH_PORT", "8000")), log_level="info", workers=1)
    return 0


def cmd_e2e(args: argparse.Namespace) -> int:
    from cvmatch.api.e2e import create_database, run_e2e
    from cvmatch.core.db import db_url

    url = args.url or db_url()
    if args.fresh_db:
        from datetime import datetime

        name = f"cvmatch_e2e_{datetime.now():%Y%m%d_%H%M%S}"
        url = create_database(url, name)
        print(f"database moi: {name} (giu lai sau khi chay)")
    s = run_e2e(args.cv_dir, args.jd, url=url, config_dir=args.config_dir, kb_dir=args.kb_dir,
                fake=args.fake_encoder, out_dir=args.out, n_explain=args.explain_top, ref_ym=args.ref_ym,
                N=args.n, K=args.k)
    print("phien ban:", json.dumps(s["versions"], ensure_ascii=False))
    print("CV:", s["cv_status"], "· JD:", ", ".join(f"{j['jd_id']} {j['status']}" for j in s["jd_status"]))
    print("thoi gian (s):", json.dumps(s["timings"], ensure_ascii=False))
    print("bo nho:", json.dumps(s["memory"], ensure_ascii=False))
    ok = True
    for r in s["runs"]:
        if r["status"] != "ok":
            ok = False
            print(f"\n{r['jd_id']}: {r['status']} {r.get('detail')}")
            continue
        t = r["timings"]
        print(f"\n== {r['jd_id']} v{r['jd_version']} · rerank run {r['run_id']} · pool {r['n_pool']}"
              f" · retrieve {t['retrieve_s']}s · rerank {t['rerank_s']}s · explain {t['explain_top_s']}s")
        for it in r["rerank_top"][:10]:
            print(f"  {it['rank']:>3} {it['score']:>3} {it['band']:<4} {'cap' if it['cap_applied'] else '   '} {it['cv_id']}"
                  f" {','.join(it['flags'])}")
        for e in r["explanations"][:1]:
            print("\n  -- giai thich hang 1 --\n  " + e["text"].replace("\n", "\n  "))
    print(f"\nbao cao: {s['dir']}/report.md\nlog: {s['log']}")
    return 0 if ok else 1


def register(sub: argparse._SubParsersAction) -> None:
    api = sub.add_parser("api", help="dich vu HTTP cho backend Java")
    apis = api.add_subparsers(dest="cmd", required=True)
    sv = apis.add_parser("serve", help="chay FastAPI (uvicorn)")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8090)
    sv.add_argument("--fake-encoder", action="store_true")
    sv.add_argument("--config-dir", default=None)
    sv.add_argument("--url", default=None)
    sv.set_defaults(func=cmd_serve)
    pr = apis.add_parser("prod", help="container: cho DB, migrate, nap KB neu chua co, roi chay API (cau hinh bang env)")
    pr.set_defaults(func=cmd_prod)

    e = sub.add_parser("run-e2e", help="chay tron: migrate -> KB -> nap CV, JD -> retrieve -> rerank -> explain")
    e.add_argument("--cv-dir", required=True)
    e.add_argument("--jd", required=True, help="file JD JSON (hoac thu muc nhieu JD)")
    e.add_argument("--kb-dir", default=None, help="thu muc snapshot KB; chua nap thi nap (mac dinh: ban trong active.yaml)")
    e.add_argument("--fake-encoder", action="store_true", help="FakeEncoder (khong GPU)")
    e.add_argument("--fresh-db", action="store_true", help="tao database moi tren cung server cho lan chay nay")
    e.add_argument("--out", default="research/reports/e2e")
    e.add_argument("--explain-top", type=int, default=5)
    e.add_argument("--n", type=int, default=None)
    e.add_argument("--k", type=int, default=None)
    e.add_argument("--ref-ym", default=None)
    e.add_argument("--config-dir", default=None)
    e.add_argument("--url", default=None)
    e.set_defaults(func=cmd_e2e)
