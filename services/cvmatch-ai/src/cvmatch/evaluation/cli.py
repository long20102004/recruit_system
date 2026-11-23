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


def cmd_coverage(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.evaluation.coverage import coverage_from_dirs

    if not args.cv and not args.jd:
        print("can --cv va/hoac --jd")
        return 2
    cfg = load_config(args.config_dir)
    tok, unit = None, "từ"
    if args.tokenizer:
        from transformers import AutoTokenizer

        e = cfg.models.embed
        hf = AutoTokenizer.from_pretrained(e.model, revision=e.revision)
        tok, unit = (lambda s: hf.tokenize(s)), "token bge-m3"
    rep = coverage_from_dirs(args.cv, args.jd, cfg, tokenizer=tok, len_unit=unit)
    md = rep.to_markdown()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md, encoding="utf-8")
    print(f"CV {rep.n_cv}/{rep.n_cv_files} hop le · JD {rep.n_jd}/{rep.n_jd_files} hop le -> {args.out}")
    for f in rep.features:
        on, failed = rep.feature_on(f)
        print(f"  {f}: {'-' if on is None else ('bat' if on else 'TAT (' + ', '.join(failed) + ')')}")
    print("de xuat features_enabled:", rep.suggested_features())
    return 0


def _cfg_enc(args, overrides=None):
    from cvmatch.api.services import config_and_encoder

    if getattr(args, "kb_version", None):
        overrides = {**(overrides or {}), "ontology_version": args.kb_version}
    return config_and_encoder(args.config_dir, fake=True if getattr(args, "fake_encoder", False) else None,
                              overrides=overrides)


def _extra(cfg) -> dict:
    """Ghi de chung cho moi cau hinh ablation: giu ban KB + khoa embed cua kho dang danh gia."""
    return {"ontology_version": cfg.ontology_version, "models": {"embed": {"key": cfg.models.embed.key}}}


def cmd_ablation(args: argparse.Namespace) -> int:
    from cvmatch.evaluation import ablation
    from cvmatch.evaluation.labels import load_graded

    labels = load_graded(args.labels)
    queries = None
    if args.split:
        split = json.loads(Path(args.split).read_text(encoding="utf-8"))
        queries = [q for q, part in split.items() if part == args.part and q in set(labels.queries)]
    groups = json.loads(Path(args.groups).read_text(encoding="utf-8")) if args.groups else None
    cfg, enc = _cfg_enc(args)
    plan = ablation.load_plan(args.plan)
    rep = ablation.run_ablation(plan, labels, url=args.url, encoder=enc, queries=queries, config_dir=args.config_dir,
                                extra_overrides=_extra(cfg), ref_ym=args.ref_ym, groups=groups,
                                only=args.only.split(",") if args.only else None)
    out = ablation.write_report(rep, args.out)
    print(ablation.to_markdown(rep))
    print(f"-> {out}")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.evaluation.labels import load_graded, split_dev_test

    labels = load_graded(args.labels)
    with connect(args.url) as conn:
        if args.direction == "jd_to_cv":
            grp = {r["jd_id"]: r["role_group"] for r in conn.execute(
                "SELECT m.jd_id, m.role_group FROM jd_meta m JOIN jd USING (jd_id, version) WHERE jd.is_latest")}
        else:
            grp = {str(r["cv_id"]): r["role_group"] for r in conn.execute("SELECT cv_id, role_group FROM cv_meta")}
    split = split_dev_test({q: grp.get(q) for q in labels.queries}, seed=args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(split, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    Path(args.out).with_suffix(".groups.json").write_text(
        json.dumps({q: grp.get(q) for q in labels.queries}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"dev {list(split.values()).count('dev')} · test {list(split.values()).count('test')} -> {args.out}")
    return 0


def cmd_kappa(args: argparse.Namespace) -> int:
    from cvmatch.evaluation.labels import kappa_report, load_graded

    print(json.dumps(kappa_report(load_graded(args.labels)), ensure_ascii=False, indent=2))
    return 0


def cmd_pool(args: argparse.Namespace) -> int:
    """Gop top-300 Retrieve cua moi RT-*, top-60 Rerank cua moi R-* + 20 ngau nhien -> CSV can cham."""
    from cvmatch.core.config import _deep_merge, load_config
    from cvmatch.core.db import connect
    from cvmatch.evaluation import ablation
    from cvmatch.evaluation.labels import load_graded
    from cvmatch.evaluation.labels.pooling import pool_items, write_pool_csv
    from cvmatch.rerank.run import Reranker
    from cvmatch.retrieve.flow_c import retrieve_for_jd

    from cvmatch.core.models import get_encoder

    cfg0, enc = _cfg_enc(args)
    enc = enc or get_encoder(cfg0, fake=False)
    extra = _extra(cfg0)
    queries = args.queries.split(",") if args.queries else None
    already = set(load_graded(args.existing).final) if args.existing else None
    runs: dict[str, dict[str, list[str]]] = {}
    with connect(args.url) as conn:
        if queries is None:
            queries = [r["jd_id"] for r in conn.execute("SELECT jd_id FROM jd WHERE is_latest AND status = 'open'"
                                                        " ORDER BY jd_id")]
        all_items = [str(r["cv_id"]) for r in conn.execute("SELECT cv_id FROM cv WHERE status = 'active' AND is_latest")]
        cache = ablation._Cache(conn, enc)
        for path, depth in ((args.retrieve_plan, 300), (args.rerank_plan, 60)):
            plan = ablation.load_plan(path)
            for c in plan.configs:
                if c.todo:
                    continue
                cfg = load_config(args.config_dir, overrides=_deep_merge(_deep_merge(plan.base, c.overrides), extra))
                idx = cache.cv_index(cfg)
                rr = Reranker(cfg, cache.bert(cfg), cache.snapshot(cfg)) if plan.stage == "rerank" and \
                    c.mode != "retrieve_only" else None
                runs[c.id] = {}
                for q in queries:
                    res = retrieve_for_jd(conn, idx, cfg, q, K=max(depth, plan.K or 0) if rr is None else plan.K,
                                          write_log=False)
                    ids = [it["cv_id"] for it in res.items]
                    if rr is not None:
                        req = res.request.model_copy(update={"N": len(res.request.candidates)})
                        ids = [r.cv_id for r in rr.rerank(conn, req, ref_ym=args.ref_ym, write=False).rows]
                    runs[c.id][q] = ids[:depth]
    pooled = pool_items(runs, all_items, n_random=args.n_random, seed=args.seed, already=already)
    n = write_pool_csv(args.out, pooled)
    print(f"{len(pooled)} truy van, {sum(len(v) for v in pooled.values())} cap can cham ({n} dong) -> {args.out}")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.core.kb.matcher import SkillMatcher
    from cvmatch.core.kb.snapshot import KBSnapshot
    from cvmatch.core.kb.store import load_snapshot_db
    from cvmatch.evaluation.calibrate import calibrate_pairs
    from cvmatch.evaluation.labels import load_pairs
    from cvmatch.rerank.bertscore.engine import BertScorer

    cfg, enc = _cfg_enc(args)
    if enc is None:
        from cvmatch.core.models import get_encoder
        enc = get_encoder(cfg, fake=False)
    if args.kb_dir:
        snap = KBSnapshot.from_dir(args.kb_dir)
    else:
        with connect(args.url) as conn:
            snap = load_snapshot_db(conn, cfg.ontology_version)
    cal = calibrate_pairs(load_pairs(args.pairs), BertScorer(enc, cfg.bertscore, SkillMatcher(snap)), encoder=enc)
    print(f"so cap: {cal.n} · AUC BERTScore {cal.auc_bertscore} · AUC cosine cau {cal.auc_cosine}")
    print("De xuat (dua vao config moi, vd rr-1.2.yaml - KHONG tu sua):\n" + cal.yaml_snippet())
    return 0


def _svc_fresh(args):
    """Services tren DB rieng (tao moi) cho thi nghiem nap du lieu (bat bien, G2)."""
    from datetime import datetime

    from cvmatch.api.e2e import create_database
    from cvmatch.api.services import Services
    from cvmatch.core.db import connect, db_url, migrate
    from cvmatch.core.kb.store import import_snapshot, read_snapshot_dir

    url = create_database(args.url or db_url(), f"cvmatch_eval_{datetime.now():%Y%m%d_%H%M%S}")
    migrate(url)
    with connect(url) as conn:
        version = import_snapshot(conn, args.kb_dir) if args.kb_dir else None
    cfg, enc = _cfg_enc(args, {"ontology_version": version} if version else None)
    print(f"database rieng: {url.split('dbname=')[-1] if 'dbname=' in url else url}")
    return Services(cfg, url=url, encoder=enc, hmac_key="eval-local-key")


def cmd_invariance(args: argparse.Namespace) -> int:
    from cvmatch.evaluation.invariance import run_invariance

    cvs = [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(Path(args.cv_dir).glob("*.json"))]
    cvs = cvs[: args.limit]
    jd_p = Path(args.jd)
    jds = [json.loads(f.read_text(encoding="utf-8")) for f in (sorted(jd_p.glob("*.json")) if jd_p.is_dir() else [jd_p])]
    with _svc_fresh(args) as svc:
        rep = run_invariance(svc, cvs, jds, ref_ym=args.ref_ym)
    md = rep.to_markdown()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md, encoding="utf-8")
    print(md)
    return 0 if rep.ok() else 1


def cmd_g2(args: argparse.Namespace) -> int:
    from cvmatch.evaluation.g2 import run_g2, to_markdown

    with _svc_fresh(args) as svc:
        rows = run_g2(svc, ref_ym=args.ref_ym)
        md = to_markdown(rows, svc.encoder.key())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md, encoding="utf-8")
    print(md)
    return 0 if all(r.passed is not False for r in rows) else 1


def cmd_prep_sample(args: argparse.Namespace) -> int:
    from cvmatch.core.db import connect
    from cvmatch.evaluation.prep_quality import export_sample

    with connect(args.url) as conn:
        names = {r["skill_id"]: r["name"] for r in conn.execute(
            "SELECT DISTINCT ON (skill_id) skill_id, name FROM skill_ontology ORDER BY skill_id")}
        print(export_sample(conn, args.out, n_cv=args.n_cv, n_jd=args.n_jd, seed=args.seed, names=names))
    return 0


def cmd_fp16(args: argparse.Namespace) -> int:
    from cvmatch.core.config import load_config
    from cvmatch.core.db import connect
    from cvmatch.core.kb.snapshot import KBSnapshot
    from cvmatch.core.kb.store import load_snapshot_db
    from cvmatch.evaluation.fp16_check import check_fp16

    cfg = load_config(args.config_dir)
    if args.kb_dir:
        snap = KBSnapshot.from_dir(args.kb_dir)
    else:
        with connect(args.url) as conn:
            snap = load_snapshot_db(conn, cfg.ontology_version)
    res = check_fp16(cfg, snap, threshold=args.threshold)
    md = res.to_markdown()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md, encoding="utf-8")
    print(md)
    return 0


def cmd_prep_score(args: argparse.Namespace) -> int:
    from cvmatch.evaluation.prep_quality import score_sample

    print(json.dumps(score_sample(args.path), ensure_ascii=False, indent=2))
    return 0


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

    c = evs.add_parser("coverage", help="do phu Module 1 (T07): truong nao du de bat feature nao")
    c.add_argument("--cv", default=None, help="thu muc / file CV JSON")
    c.add_argument("--jd", default=None, help="thu muc / file JD JSON")
    c.add_argument("--out", default="reports/coverage.md")
    c.add_argument("--tokenizer", action="store_true", help="do do dai gach bang tokenizer bge-m3 (mac dinh: so tu)")
    c.add_argument("--config-dir", default=None)
    c.set_defaults(func=cmd_coverage)

    def common(x, *, enc=True):
        x.add_argument("--config-dir", default=None)
        x.add_argument("--url", default=None)
        x.add_argument("--kb-version", default=None, help="ontology_version cua kho dang danh gia (mac dinh active.yaml)")
        if enc:
            x.add_argument("--fake-encoder", action="store_true")

    a = evs.add_parser("ablation", help="T14: chay ke hoach thi nghiem (experiments/*.yaml) -> bang + bieu do")
    a.add_argument("plan")
    a.add_argument("--labels", required=True, help="graded.csv (query_id,item_id,grade,rater)")
    a.add_argument("--split", default=None, help="file JSON {query_id: dev|test} (eval split)")
    a.add_argument("--part", default="dev", choices=["dev", "test"])
    a.add_argument("--groups", default=None, help="JSON {query_id: nhom} de tach bang theo nhom")
    a.add_argument("--only", default=None, help="chi chay cac id, vd R-A0,P1")
    a.add_argument("--ref-ym", default=None)
    a.add_argument("--out", default="reports/ablation")
    common(a)
    a.set_defaults(func=cmd_ablation)

    sp = evs.add_parser("split", help="T14: chia dev/test 50/50 phan tang theo nhom vai tro")
    sp.add_argument("--labels", required=True)
    sp.add_argument("--direction", default="jd_to_cv", choices=["jd_to_cv", "cv_to_jd"])
    sp.add_argument("--seed", type=int, default=13)
    sp.add_argument("--out", default="reports/labels/split.json")
    common(sp, enc=False)
    sp.set_defaults(func=cmd_split)

    k = evs.add_parser("kappa", help="T14: do dong thuan hai nguoi cham (kappa, kappa trong so)")
    k.add_argument("labels")
    k.set_defaults(func=cmd_kappa)

    po = evs.add_parser("pool", help="T14: gop top-300 RT-*, top-60 R-*, 20 ngau nhien -> CSV can cham")
    po.add_argument("--retrieve-plan", default="experiments/retrieve_RT.yaml")
    po.add_argument("--rerank-plan", default="experiments/rerank_R.yaml")
    po.add_argument("--queries", default=None, help="jd_id cach nhau dau phay (mac dinh: moi JD mo)")
    po.add_argument("--existing", default=None, help="file nhan da co: bo cac cap da cham")
    po.add_argument("--n-random", type=int, default=20)
    po.add_argument("--seed", type=int, default=13)
    po.add_argument("--ref-ym", default=None)
    po.add_argument("--out", default="reports/labels/to_label.csv")
    common(po)
    po.set_defaults(func=cmd_pool)

    ca = evs.add_parser("calibrate", help="T14: lo/hi + nguong muc khop tu tap ~300 cap co nhan (in, khong sua)")
    ca.add_argument("pairs", help="pairs.csv (pair_id,jd_text,cv_text,label,rater)")
    ca.add_argument("--kb-dir", default=None)
    common(ca)
    ca.set_defaults(func=cmd_calibrate)

    iv = evs.add_parser("invariance", help="T14: thu nghiem bat bien qua ca pipeline (DB rieng)")
    iv.add_argument("--cv-dir", required=True)
    iv.add_argument("--jd", required=True)
    iv.add_argument("--kb-dir", default=None)
    iv.add_argument("--limit", type=int, default=50)
    iv.add_argument("--ref-ym", default=None)
    iv.add_argument("--out", default="reports/invariance.md")
    common(iv)
    iv.set_defaults(func=cmd_invariance)

    g2 = evs.add_parser("g2", help="T14: golden co diem yeu qua ca pipeline (DB rieng)")
    g2.add_argument("--kb-dir", default=None)
    g2.add_argument("--ref-ym", default=None)
    g2.add_argument("--out", default="reports/g2.md")
    common(g2)
    g2.set_defaults(func=cmd_g2)

    ps = evs.add_parser("prep-sample", help="T14: lay mau 50 CV + 30 JD cho nguoi kiem tien xu ly")
    ps.add_argument("--n-cv", type=int, default=50)
    ps.add_argument("--n-jd", type=int, default=30)
    ps.add_argument("--seed", type=int, default=13)
    ps.add_argument("--out", default="reports/prep_sample.jsonl")
    common(ps, enc=False)
    ps.set_defaults(func=cmd_prep_sample)

    f16 = evs.add_parser("fp16", help="T17: kiem lech fp16 so voi fp32 tren golden (< 0,001 moi duoc chuyen)")
    f16.add_argument("--kb-dir", default=None)
    f16.add_argument("--threshold", type=float, default=0.001)
    f16.add_argument("--out", default="reports/fp16_check.md")
    f16.add_argument("--config-dir", default=None)
    f16.add_argument("--url", default=None)
    f16.set_defaults(func=cmd_fp16)

    pc = evs.add_parser("prep-score", help="T14: cham file mau tien xu ly da dien gold")
    pc.add_argument("path")
    pc.set_defaults(func=cmd_prep_score)

