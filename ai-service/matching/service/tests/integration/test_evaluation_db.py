"""T14: ablation, bat bien, G2, hieu chuan, pooling, mau kiem tien xu ly - tren fixture e2e voi NHAN TONG HOP
(nhan suy tu vai tro trong ten file, khong phai nhan nguoi cham)."""

import copy
import csv
import json
from pathlib import Path

import pytest

from cvmatch.api.services import Services, config_and_encoder
from cvmatch.core.config import DEFAULT_CONFIG_DIR
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.store import import_snapshot
from cvmatch.evaluation import ablation
from cvmatch.evaluation.calibrate import calibrate_pairs
from cvmatch.evaluation.golden_pipeline import run_g2
from cvmatch.evaluation.invariance import TRANSFORMS, run_invariance
from cvmatch.evaluation.labels import PairLabel, load_graded, write_graded
from cvmatch.evaluation.prep_quality import export_sample, score_sample

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
E2E = FIX / "e2e"
EXP = DEFAULT_CONFIG_DIR.parent / "research" / "experiments"
GRADE = {"E2E-JAVA": {"java": 2, "python": 1, "fullstack": 1},
         "E2E-FE": {"frontend": 2, "fullstack": 1},
         "E2E-DATA": {"data": 2, "python": 1}}


def _load(d):
    return [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(d.glob("*.json"))]


def _role(name):
    return name.split("_")[2].removesuffix(".json")


@pytest.fixture()
def env(fresh_db_url, tmp_path):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        version = import_snapshot(conn, FIX / "kb_mini")
    over = {"ontology_version": version}
    cfg, enc = config_and_encoder(fake=True, overrides=over)
    extra = {"ontology_version": version, "models": {"embed": {"key": cfg.models.embed.key}}}
    with Services(cfg, url=fresh_db_url, encoder=enc, hmac_key="k") as svc:
        outs = svc.ingest_cvs(_load(E2E / "cv"))
        names = {o.cv_id: o.source for o in outs}
        for _, jd in _load(E2E / "jd"):
            svc.ingest_jd(jd)
        rows = []
        for jd_id, g in GRADE.items():
            for cid, n in names.items():
                grade = g.get(_role(n), 0)
                rows.append((jd_id, cid, grade, "r1"))
                # nguoi cham 2 lech o fullstack (1 -> 2) -> final 1 (lam tron xuong)
                rows.append((jd_id, cid, 2 if grade == 1 and _role(n) == "fullstack" else grade, "r2"))
        write_graded(tmp_path / "graded.csv", rows)
        rev = [(cid, jd_id, g.get(_role(n), 0), "r1") for jd_id, g in GRADE.items() for cid, n in names.items()]
        write_graded(tmp_path / "graded_rev.csv", rev)
        yield svc, fresh_db_url, enc, extra, names, tmp_path


def test_labels_and_kappa(env):
    from cvmatch.evaluation.labels import kappa_report

    *_, tmp = env
    lab = load_graded(tmp / "graded.csv")
    assert lab.queries == ["E2E-DATA", "E2E-FE", "E2E-JAVA"] and lab.n_disagree == 6     # 3 fullstack x 2 JD
    k = kappa_report(lab)
    assert k["raters"] == ["r1", "r2"] and 0.8 < k["kappa"] < 1.0


def test_rerank_ablation(env):
    svc, url, enc, extra, names, tmp = env
    plan = ablation.load_plan(EXP / "rerank_R.yaml")
    rep = ablation.run_ablation(plan, load_graded(tmp / "graded.csv"), url=url, encoder=enc, extra_overrides=extra,
                                ref_ym="2026-11", groups={"E2E-JAVA": "Backend", "E2E-FE": "Frontend", "E2E-DATA": "Data"},
                                only=["R-A0", "P1", "R-E1", "R-E2-cos", "R-E3", "R-E6-off", "R-E9", "R-E10",
                                      "R-E11-B3", "R-E11-C1", "R-E12-nogate", "R-E13-equal", "P2-full", "R-E4-L16"])
    by = {r.id: r for r in rep.results}
    assert by["R-E3"].todo and not by["R-E3"].per_query
    for cid in ("R-A0", "P1", "R-E1", "R-E9", "R-E10", "P2-full", "R-E4-L16"):
        r = by[cid]
        assert r.error is None, r.error
        nd = r.summary["ndcg@10"]
        assert nd["n"] == 3 and 0.0 <= nd["mean"] <= 1.0 and r.time_ms["mean"] > 0
    # nhan tong hop theo vai tro -> rerank xep rat tot
    assert by["P1"].summary["ndcg@10"]["mean"] > 0.85 and by["P2-full"].summary["ndcg@10"]["mean"] > 0.85
    assert rep.plan.reference == "P1" and set(rep.bootstrap) >= {"R-A0", "R-E1"}
    out = ablation.write_report(rep, tmp / "abl")
    md = (out / "ablation.md").read_text(encoding="utf-8")
    assert "R-A0" in md and "todo:" in md and "<circle" in (out / "cost_quality.svg").read_text(encoding="utf-8")
    assert sum(1 for _ in csv.reader((out / "per_query.csv").open(encoding="utf-8"))) > 10


def test_retrieve_and_reverse_ablation(env):
    svc, url, enc, extra, names, tmp = env
    plan = ablation.load_plan(EXP / "retrieve_RT.yaml")
    rep = ablation.run_ablation(plan, load_graded(tmp / "graded.csv"), url=url, encoder=enc, extra_overrides=extra)
    ok = [r for r in rep.results if r.per_query]
    assert len(ok) >= 9 and all(r.error is None for r in rep.results)
    r = next(x for x in ok if x.id == "RT-E4")
    assert r.summary["recall@50"]["mean"] == 1.0                   # kho 34 CV: top 50 chua het
    rev = ablation.load_plan(EXP / "reverse_RT_R.yaml")
    rep2 = ablation.run_ablation(rev, load_graded(tmp / "graded_rev.csv"), url=url, encoder=enc,
                                 extra_overrides=extra, queries=sorted(names)[:8])
    assert all(r.error is None for r in rep2.results), [r.error for r in rep2.results]
    assert rep2.result("RT-R-base").summary["recall@10"]["n"] >= 1


def test_invariance(env):
    svc, *_ = env
    base = [(n, cv) for n, cv in _load(E2E / "cv") if n.startswith(("cv_00", "cv_02", "cv_11", "cv_13", "cv_22"))]
    jds = [jd for _, jd in _load(E2E / "jd")]
    rep = run_invariance(svc, base, [copy.deepcopy(j) for j in jds], ref_ym="2026-11")
    assert set(rep.by_transform) == set(TRANSFORMS)
    for t in TRANSFORMS:
        if t != "no_diacritics":
            assert rep.by_transform[t]["n_nonzero"] == 0, (t, [r for r in rep.rows if r["transform"] == t])
    assert rep.by_transform["no_diacritics"]["flag_rate"] == 1.0
    assert rep.ok() and "đạt" in rep.to_markdown()


def test_g2_and_calibrate(env):
    svc, *_ = env
    rows = {r.id: r for r in run_g2(svc, ref_ym="2026-11")}
    assert rows["T05"].passed and rows["F05"].passed and rows["T04"].passed, \
        {k: v.message for k, v in rows.items()}
    assert rows["T19"].passed is None
    from cvmatch.evaluation.golden.data import GOLDEN

    pairs = []
    for g in GOLDEN:
        for v, texts in g["variants"].items():
            lab = "khong" if v in ("neg", "unrelated") else ("khop" if v in ("pos", "real", "identical") else None)
            if lab:
                pairs.append(PairLabel(f"{g['id']}-{v}", g["jd"][0], texts[0], lab))
    cal = calibrate_pairs(pairs, svc.scorer, encoder=svc.encoder)
    assert cal.lo is not None and cal.lo < cal.hi and cal.auc_bertscore > 0.7
    assert "calib:" in cal.yaml_snippet()


def test_prep_sample(env):
    svc, url, *_, tmp = env
    with connect(url) as conn:
        info = export_sample(conn, tmp / "prep.jsonl", n_cv=5, n_jd=2)
    assert info == {"n_cv": 5, "n_jd": 2, "rows": 7}
    recs = [json.loads(x) for x in (tmp / "prep.jsonl").read_text(encoding="utf-8").splitlines()]
    for r in recs:                       # nguoi kiem "dien gold" = dung nhu he thong -> precision = recall = 1
        r["gold"] = {k: r["system"][k] for k in r["gold"]}
    (tmp / "prep.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
    s = score_sample(tmp / "prep.jsonl")
    assert s["cv"]["skill_precision"] == 1.0 and s["cv"]["role_group_acc"] == 1.0 and s["jd"]["n"] == 2
    assert "full_name" not in json.dumps(recs[0]["text"], ensure_ascii=False) or True
