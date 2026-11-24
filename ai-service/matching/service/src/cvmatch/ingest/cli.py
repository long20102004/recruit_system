"""Lenh `cvmatch ingest ...` va `cvmatch delete cv ...`."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def _load_snapshot(args):
    from cvmatch.core.kb.snapshot import KBSnapshot

    if args.kb_dir:
        return KBSnapshot.from_dir(args.kb_dir)
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.core.kb.store import load_snapshot_db

    version = getattr(args, "kb_version", None) or load_config(args.config_dir).ontology_version
    with connect(args.url) as conn:
        return load_snapshot_db(conn, version)  # None -> ban nap gan nhat


def _iter_json(path: Path):
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    for f in files:
        try:
            yield str(f), json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            # khong phai object -> A1 bao InvalidCV, ghi ingest_log 'invalid'
            yield str(f), f"JSONDecodeError: {e}"


def cmd_ingest_cv(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.core.models import get_encoder
    from cvmatch.ingest.cv.record import CvContext
    from cvmatch.ingest.cv.service import CvIngestor

    cfg = load_config(args.config_dir)
    ctx = CvContext.create(cfg, _load_snapshot(args), ingest_ym=args.ingest_ym)
    encoder = get_encoder(cfg, fake=True if args.fake_encoder else None)
    items = list(_iter_json(Path(args.path)))
    with connect(args.url) as conn:
        outcomes = CvIngestor(conn, ctx, encoder, batch_size=args.batch).ingest_many(items)
    for o in outcomes:
        if o.status != "ok" or args.verbose:
            print(f"{o.status:9s} {o.source} {o.cv_id or ''} {o.detail or ''}")
    print("Tong:", dict(Counter(o.status for o in outcomes)))
    return 0 if all(o.status in ("ok", "duplicate") for o in outcomes) else 1


def cmd_delete_cv(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.ingest.cv.service import delete_cv

    with connect(args.url) as conn:
        ok = delete_cv(conn, args.cv_id)
    print("da xoa" if ok else "khong tim thay CV")
    return 0 if ok else 1


def cmd_ingest_jd(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.core.models import get_encoder
    from cvmatch.ingest.cv.record import CvContext
    from cvmatch.ingest.jd.pipeline import JdIngestor

    cfg = load_config(args.config_dir)
    ctx = CvContext.create(cfg, _load_snapshot(args), hmac_key="unused-for-jd")
    encoder = get_encoder(cfg, fake=True if args.fake_encoder else None)
    with connect(args.url) as conn:
        outcomes = JdIngestor(conn, ctx, encoder).ingest_many(list(_iter_json(Path(args.path))))
    for o in outcomes:
        warn = ", ".join(w["code"] for w in o.warnings)
        print(f"{o.status:9s} {o.source} {o.jd_id or ''} v{o.version or ''} {warn} {o.detail or ''}")
    print("Tong:", dict(Counter(o.status for o in outcomes)))
    return 0 if all(o.status in ("ok", "unchanged") for o in outcomes) else 1


def cmd_jd_status(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.ingest.jd.pipeline import set_jd_status

    with connect(args.url) as conn:
        v = set_jd_status(conn, args.jd_id, args.status)
    print(f"{args.jd_id} v{v} -> {args.status}" if v else "khong tim thay JD")
    return 0 if v else 1


def cmd_reprocess(args: argparse.Namespace) -> int:
    from cvmatch.api.services import config_and_encoder
    from cvmatch.core.db import connect
    from cvmatch.core.models import get_encoder
    from cvmatch.ingest.cv.record import CvContext
    from cvmatch.ingest.reprocess import reprocess_cvs, reprocess_jds

    cfg, enc = config_and_encoder(args.config_dir, fake=True if args.fake_encoder else None)
    enc = enc or get_encoder(cfg, fake=False)
    snap = _load_snapshot(args)
    ctx = CvContext.create(cfg, snap)
    with connect(args.url) as conn:
        if args.entity == "cv":
            rep = reprocess_cvs(conn, ctx, enc, from_step=args.from_step, batch_size=args.batch, limit=args.limit)
        else:
            rep = reprocess_jds(conn, ctx, enc, limit=args.limit)
    print(f"reprocess {rep.entity} --from {rep.from_step or '-'} -> bo khoa {rep.keys}")
    print(f"  ung vien {rep.n_candidates} · xong {rep.n_done} · loi {rep.n_failed} · {rep.duration_s}s")
    if rep.entity == "cv":
        print(f"  dung lai vector: tai lieu {rep.reused_doc_vectors}, gach {rep.reused_bullet_vectors};"
              f" embed moi {rep.embedded_texts} van ban")
    for e in rep.errors[:20]:
        print("  loi:", e)
    print("Ban cu giu nguyen (match duoc voi cau hinh cu). Danh gia ban moi roi doi active.yaml de chuyen cung luc CV + JD.")
    return 0 if rep.n_failed == 0 else 1


def register(sub: argparse._SubParsersAction) -> None:
    ing = sub.add_parser("ingest", help="nap CV / JD (Tang 0)")
    ings = ing.add_subparsers(dest="cmd", required=True)
    cv = ings.add_parser("cv", help="nap CV JSON (file hoac thu muc)")
    cv.add_argument("path")
    cv.add_argument("--kb-dir", default=None, help="thu muc snapshot KB (mac dinh: doc tu Postgres)")
    cv.add_argument("--kb-version", default=None, help="ontology_version trong Postgres (mac dinh: active.yaml hoac ban moi nhat)")
    cv.add_argument("--batch", type=int, default=32)
    cv.add_argument("--ingest-ym", default=None, help="thang nap YYYY-MM (mac dinh: thang hien tai)")
    cv.add_argument("--fake-encoder", action="store_true", help="dung FakeEncoder (khong can GPU)")
    cv.add_argument("--config-dir", default=None)
    cv.add_argument("--url", default=None)
    cv.add_argument("-v", "--verbose", action="store_true")
    cv.set_defaults(func=cmd_ingest_cv)

    jd = ings.add_parser("jd", help="nap JD JSON (file hoac thu muc)")
    jd.add_argument("path")
    jd.add_argument("--kb-dir", default=None, help="thu muc snapshot KB (mac dinh: doc tu Postgres)")
    jd.add_argument("--kb-version", default=None)
    jd.add_argument("--fake-encoder", action="store_true")
    jd.add_argument("--config-dir", default=None)
    jd.add_argument("--url", default=None)
    jd.set_defaults(func=cmd_ingest_jd)

    jds = sub.add_parser("jd", help="quan ly JD")
    jdss = jds.add_subparsers(dest="cmd", required=True)
    st = jdss.add_parser("status", help="doi trang thai JD (khong tinh lai vector)")
    st.add_argument("jd_id")
    st.add_argument("status", choices=["open", "draft", "closed", "expired"])
    st.add_argument("--url", default=None)
    st.set_defaults(func=cmd_jd_status)

    rp = sub.add_parser("reprocess", help="chay lai Luong A/B toan kho khi KB / chuan hoa / model doi (ghi song song)")
    rp.add_argument("entity", choices=["cv", "jd"])
    rp.add_argument("--from", dest="from_step", default="A5", choices=["A5", "A8", "A10"],
                    help="A5: KB moi (giu vector) · A8: doi chuan hoa/mau ghep · A10: doi model embedding")
    rp.add_argument("--kb-dir", default=None)
    rp.add_argument("--kb-version", default=None)
    rp.add_argument("--batch", type=int, default=32)
    rp.add_argument("--limit", type=int, default=None)
    rp.add_argument("--fake-encoder", action="store_true")
    rp.add_argument("--config-dir", default=None)
    rp.add_argument("--url", default=None)
    rp.set_defaults(func=cmd_reprocess)

    de = sub.add_parser("delete", help="xoa du lieu theo yeu cau")
    des = de.add_subparsers(dest="cmd", required=True)
    dcv = des.add_parser("cv")
    dcv.add_argument("cv_id")
    dcv.add_argument("--url", default=None)
    dcv.set_defaults(func=cmd_delete_cv)
