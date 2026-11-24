"""T11: Rerank RR1-RR6 tren Postgres that (FakeEncoder, KB mini)."""

import copy
import json
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.models import FakeEncoder
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.service import CvIngestor
from cvmatch.ingest.jd.pipeline import JdIngestor
from cvmatch.rerank.bertscore.engine import BertScorer
from cvmatch.rerank.run import Reranker, request_from_run
from cvmatch.retrieve.flow_c import retrieve_for_jd
from cvmatch.retrieve.index import CvIndex

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
CV = json.loads((FIX / "cv" / "cv_sample.json").read_text(encoding="utf-8"))
JD = json.loads((FIX / "jd" / "jd_sample.json").read_text(encoding="utf-8"))
KEY = "fake-bge-m3@5617a9f61b"


def cv(email, title, bullets, skills, location="TP.HCM", start="2020-01"):
    d = copy.deepcopy(CV)
    d.update(email=email, skills=skills, location=location, summary=title)
    d["experiences"] = [{"title": title, "start": start, "end": None, "is_current": True,
                         "description": bullets, "technologies": []}]
    return d


POOL = {
    "backend": cv("b@x", "Senior Java Developer", ["Thiết kế và phát triển API cho hệ thống thanh toán bằng Spring Boot",
                                                    "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL"],
                  ["Java", "Spring Boot", "PostgreSQL", "Kafka"]),
    "backend_py": cv("p@x", "Python Developer", ["Phát triển API thanh toán bằng Django",
                                                 "Tối ưu truy vấn cơ sở dữ liệu MySQL cho báo cáo"], ["Python", "Django"],
                     start="2024-01"),
    "frontend": cv("f@x", "Frontend Developer", ["Xây dựng giao diện React cho trang quản trị",
                                                 "Tối ưu tốc độ tải trang web"], ["React", "JavaScript"], location="Hà Nội"),
    "designer": cv("d@x", "Designer", ["Thiết kế banner quảng cáo, chỉnh sửa ảnh Photoshop"], ["Photoshop"]),
    "no_bullets": cv("n@x", "Java Developer", [], ["Java", "Spring Boot"]),
    "no_acc": cv("a@x", "Java Developer", ["Thiet ke va phat trien API cho he thong thanh toan bang Spring Boot",
                                          "Toi uu hieu nang truy van co so du lieu PostgreSQL"],
                 ["Java", "Spring Boot", "PostgreSQL"]),
}


@pytest.fixture()
def env(fresh_db_url):
    migrate(fresh_db_url)
    snap = KBSnapshot.from_dir(FIX / "kb_mini")
    cfg = load_config(overrides={"ontology_version": snap.ontology_version, "models": {"embed": {"key": KEY}}})
    ctx = CvContext.create(cfg, snap, hmac_key="k", ingest_ym="2026-11")
    enc = FakeEncoder(key=KEY)
    with connect(fresh_db_url) as conn:
        outs = CvIngestor(conn, ctx, enc).ingest_many([(k, v) for k, v in POOL.items()])
        names = {o.cv_id: k for (k, _), o in zip(POOL.items(), outs)}
        assert JdIngestor(conn, ctx, enc).ingest_one(copy.deepcopy(JD)).status == "ok"
        idx = CvIndex(cfg).build(conn)
        rr = Reranker(cfg, BertScorer(enc, cfg.bertscore, SkillMatcher(snap)), snap)
        yield conn, cfg, idx, names, ctx, enc, rr


def test_rerank_end_to_end(env):
    conn, cfg, idx, names, _, _, rr = env
    res = retrieve_for_jd(conn, idx, cfg, "JD-0412")
    out = rr.rerank(conn, res.request, ref_ym="2026-11")
    by = {names[f.cv_id]: f for f in out.rows}
    order = [names[f.cv_id] for f in out.rows]
    assert order[0] == "backend" and order.index("designer") > order.index("backend_py")
    top = out.items[0]
    assert names[top.cv_id] == "backend" and top.rank == 1 and not top.cap_applied
    # B4: 2 trach nhiem khong chung chung (bo "Tham gia cac buoi hop"), gach giong het -> R = 1 -> khop
    assert [d.level for d in by["backend"].resp_detail] == ["met", "met"]
    assert all(f.evidence_id in top.evidence for f in top.resp_facts)
    assert top.evidence[top.resp_facts[0].evidence_id].text_raw.startswith("Thiết kế và phát triển API")
    assert top.skill_facts.missing == [] and len(top.skill_facts.met) == 3
    assert top.experience_facts.role_group_jd == "Backend" and top.experience_facts.relevant_years > 6
    # thieu phia CV -> trung vi pool + co
    assert by["no_bullets"].missing == {"B4": "cv_side"} and by["no_acc"].missing == {"B4": "cv_side"}
    assert "no_diacritics" in by["no_acc"].flags
    scored_b4 = sorted(by[k].features.B4 for k in ("backend", "backend_py", "frontend", "designer"))
    assert by["no_bullets"].features.B4 == pytest.approx((scored_b4[1] + scored_b4[2]) / 2)
    # cong must-have: designer khong co ky nang bat buoc -> A1 = 0 -> cap 50
    assert by["designer"].features.A1 == 0 and by["designer"].gate_cap == 50
    assert "location_mismatch" in by["frontend"].flags
    # RR6
    run = conn.execute("SELECT * FROM rerank_run WHERE run_id = %s", (out.run_id,)).fetchone()
    assert run["retrieve_run_id"] is not None and run["config_json"]["ref_ym"] == "2026-11"
    n_feat = conn.execute("SELECT count(*) AS n FROM rerank_feature WHERE run_id = %s", (out.run_id,)).fetchone()["n"]
    n_res = conn.execute("SELECT count(*) AS n FROM rerank_result WHERE run_id = %s", (out.run_id,)).fetchone()["n"]
    assert n_feat == 6 and n_res == 6


def test_rerank_reproducible_and_from_run(env):
    conn, cfg, idx, names, _, _, rr = env
    res = retrieve_for_jd(conn, idx, cfg, "JD-0412")
    a = rr.rerank(conn, res.request, ref_ym="2026-11")
    req2 = request_from_run(conn, cfg, res.run_id, N=3)
    b = rr.rerank(conn, req2, ref_ym="2026-11")
    assert len(b.items) == 3
    fa = [it.model_dump() for it in a.items[:3]]
    fb = [it.model_dump() for it in b.items]
    for x, y in zip(fa, fb):
        for k in x:
            assert x[k] == y[k], (k, x[k], y[k])
    rows = lambda rid: conn.execute(  # noqa: E731
        "SELECT item_id, rank, score, score_raw, cap_applied, facts_json FROM rerank_result"
        " WHERE run_id = %s ORDER BY rank", (rid,)).fetchall()
    assert rows(a.run_id)[:3] == rows(b.run_id)


def test_jd_without_responsibilities(env):
    conn, cfg, idx, names, ctx, enc, rr = env
    jd = copy.deepcopy(JD)
    jd.update(jd_id="JD-NORESP", responsibilities=["Tham gia các buổi họp của team"])
    assert JdIngestor(conn, ctx, enc).ingest_one(jd).status == "ok"
    res = retrieve_for_jd(conn, idx, cfg, "JD-NORESP")
    out = rr.rerank(conn, res.request, ref_ym="2026-11")
    assert all(f.missing.get("B4") == "jd_side" and f.features.B4 is None for f in out.rows)
    top = out.rows[0]
    f = top.features
    w = cfg.rerank.weights
    num = w["A1"] * f.A1 + w["B1"] * f.B1 + w["B2"] * f.B2
    assert top.s_raw == pytest.approx(num / (w["A1"] + w["B1"] + w["B2"]), abs=1e-5)


def test_explain_lazy_and_cached(env):
    from cvmatch.explain.service import ExplainService

    conn, cfg, idx, names, _, _, rr = env
    res = retrieve_for_jd(conn, idx, cfg, "JD-0412")
    out = rr.rerank(conn, res.request.model_copy(update={"N": 3}), ref_ym="2026-11")
    svc = ExplainService(cfg, rr.snapshot)
    top = out.items[0]
    assert conn.execute("SELECT explanation_json FROM rerank_result WHERE run_id=%s AND item_id=%s",
                        (out.run_id, top.cv_id)).fetchone()["explanation_json"] is None     # luoi: chua tao
    e1 = svc.explain(conn, out.run_id, top.cv_id)
    assert e1["text"].startswith(f"Điểm {top.score}/100")
    assert "Thiết kế và phát triển API cho hệ thống thanh toán bằng Spring Boot" in e1["text"]
    stored = conn.execute("SELECT explanation_json FROM rerank_result WHERE run_id=%s AND item_id=%s",
                          (out.run_id, top.cv_id)).fetchone()["explanation_json"]
    assert stored["cache_key"] == e1["cache_key"]
    assert svc.explain(conn, out.run_id, top.cv_id) == stored                                  # trung cache
    # CV ngoai top N: dung lai FinalItem tu rerank_feature (EX1), giong cach RR6 dung
    designer = next(f for f in out.rows if names[f.cv_id] == "designer")
    assert designer.cv_id not in {it.cv_id for it in out.items}
    e2 = svc.explain(conn, out.run_id, designer.cv_id)
    assert designer.score < designer.gate_cap and "Điểm bị giới hạn" not in e2["text"]   # diem thap hon tran
    assert "chưa thấy bằng chứng về Java, Spring Boot, PostgreSQL trong CV." in e2["text"]
    # facts dung lai tu rerank_feature khop voi facts RR6 dung truc tiep
    from cvmatch.explain.facts import load_final_item

    full = rr.rerank(conn, res.request, ref_ym="2026-11", write=False)
    direct = next(it for it in full.items if it.cv_id == designer.cv_id)
    rebuilt = load_final_item(conn, out.run_id, designer.cv_id, rels=svc.rels, names=svc.names)
    assert rebuilt.model_dump(exclude={"score_raw"}) == direct.model_dump(exclude={"score_raw"})
