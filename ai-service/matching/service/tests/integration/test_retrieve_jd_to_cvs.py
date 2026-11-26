"""T09: Luong C tren Postgres that (FakeEncoder, KB mini)."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from cvmatch.core.config import load_config
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.models import FakeEncoder
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.service import CvIngestor
from cvmatch.ingest.jd.pipeline import JdIngestor
from cvmatch.retrieve.jd_to_cvs import JdNotReady, retrieve_for_jd
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
                                                 "Tối ưu truy vấn cơ sở dữ liệu MySQL cho báo cáo"], ["Python", "Django"]),
    "frontend": cv("f@x", "Frontend Developer", ["Xây dựng giao diện React cho trang quản trị",
                                                 "Tối ưu tốc độ tải trang web"], ["React", "JavaScript"], location="Hà Nội"),
    "designer": cv("d@x", "Designer", ["Thiết kế banner quảng cáo, chỉnh sửa ảnh Photoshop"], ["Photoshop"]),
    "no_bullets": cv("n@x", "Java Developer", [], ["Java", "Spring Boot"]),
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
        yield conn, cfg, idx, names, ctx, enc


def test_ranking_logs_and_request(env):
    conn, cfg, idx, names, *_ = env
    res = retrieve_for_jd(conn, idx, cfg, "JD-0412")
    order = [names[it["cv_id"]] for it in res.items]
    assert order[0] == "backend" and order[-1] == "designer"
    assert res.views_used == ["dense", "bm25", "skill", "resp"] and res.n_pool == 5
    top = res.items[0]
    # Java chi o skills (ev 0,6) x w 1,0 + Spring Boot (mo ta, ev 1,0) x 1,0 + PostgreSQL (mo ta) x 0,7
    assert top["s"]["skill"] == pytest.approx((0.6 * 1.0 + 1.0 * 1.0 + 1.0 * 0.7) / 2.7)
    assert top["explanation"]["skills_missing"] == []
    assert top["explanation"]["top_bullets"][0]["text_raw"].startswith(("Thiết kế", "Tối ưu"))
    nb = next(it for it in res.items if names[it["cv_id"]] == "no_bullets")
    assert nb["s"]["resp"] is None and nb["explanation"]["top_bullets"] == []   # thieu du lieu, khong phai 0
    # C7
    run = conn.execute("SELECT * FROM match_run WHERE run_id = %s", (res.run_id,)).fetchone()
    assert (run["direction"], run["query_id"], run["k"], run["n_pool"]) == ("jd_to_cv", "JD-0412", 200, 5)
    assert conn.execute("SELECT count(*) AS n FROM match_result WHERE run_id = %s", (res.run_id,)).fetchone()["n"] == 5
    # C8
    req = res.request
    assert req.retrieve_run_id == res.run_id and req.N == 30 and len(req.candidates) == 5
    assert req.candidates[0].cv_id == res.items[0]["cv_id"]


def test_deterministic(env):
    conn, cfg, idx, *_ = env
    a = retrieve_for_jd(conn, idx, cfg, "JD-0412", write_log=False)
    b = retrieve_for_jd(conn, idx, cfg, "JD-0412", write_log=False)
    assert [(i["cv_id"], i["fused"]) for i in a.items] == [(i["cv_id"], i["fused"]) for i in b.items]


def test_k_exclude_and_hard_filter(env):
    conn, cfg, idx, names, *_ = env
    assert len(retrieve_for_jd(conn, idx, cfg, "JD-0412", K=2, write_log=False).items) == 2
    backend = next(c for c, n in names.items() if n == "backend")
    r = retrieve_for_jd(conn, idx, cfg, "JD-0412", exclude_cv_ids={backend}, write_log=False)
    assert backend not in [i["cv_id"] for i in r.items]
    r = retrieve_for_jd(conn, idx, cfg, "JD-0412", hard_filters={"location": "ho_chi_minh"}, write_log=False)
    assert "frontend" not in {names[i["cv_id"]] for i in r.items}            # Ha Noi bi loai
    assert any(w["code"] == "small_pool" for w in r.warnings)


def test_jd_without_required_skills_uses_three_views(env):
    conn, cfg, idx, names, ctx, enc = env
    jd = copy.deepcopy(JD)
    jd["jd_id"] = "JD-NOSKILL"
    for s in jd["skills"]:
        s["required"] = False
    JdIngestor(conn, ctx, enc).ingest_one(jd)
    r = retrieve_for_jd(conn, idx, cfg, "JD-NOSKILL", write_log=False)
    assert r.views_used == ["dense", "bm25", "resp"]
    assert any(w["code"] == "no_skill_view" for w in r.warnings)


def test_view_subset_and_missing_jd(env):
    conn, cfg, idx, *_ = env
    r = retrieve_for_jd(conn, idx, cfg, "JD-0412", views=["bm25"], write_log=False)
    assert r.views_used == ["bm25"]
    with pytest.raises(JdNotReady):
        retrieve_for_jd(conn, idx, cfg, "KHONG-CO")
