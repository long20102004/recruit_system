"""T16: Luong D tren Postgres that (FakeEncoder, KB mini): CV -> JD, rerank chieu nguoc, giai thich ung vien,
JD vua dong bi loai, CV xem truoc khong de lai dau vet."""

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cvmatch.api.app import create_app
from cvmatch.api.services import Services, config_and_encoder
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.store import import_snapshot

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
E2E = FIX / "e2e"


def _load(d):
    return [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(d.glob("*.json"))]


@pytest.fixture()
def svc(fresh_db_url):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        version = import_snapshot(conn, FIX / "kb_mini")
    cfg, enc = config_and_encoder(fake=True, overrides={"ontology_version": version})
    with Services(cfg, url=fresh_db_url, encoder=enc, hmac_key="k") as s:
        outs = s.ingest_cvs(_load(E2E / "cv"))
        s.names = {o.cv_id: Path(o.source).name for o in outs}
        for _, jd in _load(E2E / "jd"):
            assert s.ingest_jd(jd).status == "ok"
        yield s


def _cv_of(svc, prefix):
    return next(c for c, n in svc.names.items() if n.startswith(prefix))


def test_reverse_ranking_rrf_and_explain(svc):
    assert svc.jd_index.n_jd == 3                         # su kien jd_committed -> dung lai chi muc JD
    cv = _cv_of(svc, "cv_14_frontend")
    m = svc.match_cv(cv, ref_ym="2026-11")
    assert [it["jd_id"] for it in m.items][0] == "E2E-FE"
    assert any(w["code"] == "small_jd_pool_rrf" for w in m.warnings)      # 3 JD < 10 -> RRF
    assert len(m.items) == 3 and all(set(it) >= {"jd_id", "jd_version", "score", "band"} for it in m.items)
    with svc.connect() as conn:
        mr = conn.execute("SELECT direction, query_id, k FROM match_run WHERE run_id = %s",
                          (m.retrieve_run_id,)).fetchone()
        rr = conn.execute("SELECT direction, config_json FROM rerank_run WHERE run_id = %s", (m.run_id,)).fetchone()
    assert (mr["direction"], mr["query_id"], mr["k"]) == ("cv_to_jd", cv, 3)
    assert rr["direction"] == "cv_to_jd" and rr["config_json"]["cv_id"] == cv
    # phat thua tat o chieu nguoc
    assert rr["config_json"]["rerank"]["b2"]["overqual_penalty_reverse"] is False

    e = svc.explain(m.run_id, "E2E-FE")
    assert e["audience"] == "candidate" and e["jd_id"] == "E2E-FE" and e["cv_id"] == cv
    t = e["text"]
    assert t.startswith("Mức phù hợp với vị trí này:") and "CV của bạn chưa thể hiện" in t
    assert "/100" not in t                                                # khong hien diem so
    # cong must-have chieu nguoc: CV du ky nang bat buoc cua JD -> khong bi tran du A1 (co min_imp_sum) < 0,7
    for name in ("cv_00_java", "cv_02_java", "cv_03_java"):
        mj = svc.match_cv(_cv_of(svc, name), ref_ym="2026-11")
        it = next(x for x in mj.final_items if x.jd_id == "E2E-JAVA")
        if not it.skill_facts.missing:
            assert not it.cap_applied and it.gate_cap == 100 and it.features.A1 < 1.0
    data = _cv_of(svc, "cv_22_data")
    assert svc.match_cv(data, ref_ym="2026-11").items[0]["jd_id"] == "E2E-DATA"


def test_closed_jd_dropped(svc, monkeypatch):
    cv = _cv_of(svc, "cv_00_java")
    import cvmatch.api.services as S

    real = S.retrieve_for_cv

    def close_after_retrieve(conn, idx, cfg, cv_id, **kw):
        res = real(conn, idx, cfg, cv_id, **kw)
        conn.execute("UPDATE jd SET status = 'closed' WHERE jd_id = 'E2E-JAVA'")   # dong ngay sau khi tinh
        return res

    monkeypatch.setattr(S, "retrieve_for_cv", close_after_retrieve)
    m = svc.match_cv(cv, ref_ym="2026-11")
    assert "E2E-JAVA" not in [it["jd_id"] for it in m.items]
    assert any(w["code"] == "jd_closed" for w in m.warnings)


def test_api_and_preview_leaves_no_trace(svc):
    with TestClient(create_app(svc)) as c:
        cv = _cv_of(svc, "cv_14_frontend")
        r = c.post(f"/match/cv/{cv}", json={"N": 2, "ref_ym": "2026-11"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) == 2 and body["cv_id"] == cv
        e = c.get(f"/match/{body['run_id']}/jd/{body['items'][0]['jd_id']}/explain")
        assert e.status_code == 200 and e.json()["audience"] == "candidate"
        assert c.post("/match/cv/00000000-0000-0000-0000-000000000000").status_code == 404

        with svc.connect() as conn:
            before = {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
                      for t in ("cv", "cv_bullet", "ingest_log", "match_run", "rerank_run")}
        new_cv = copy.deepcopy(dict(_load(E2E / "cv"))["cv_14_frontend.json"])
        new_cv["summary"] = "Frontend developer, đã làm React và TypeScript nhiều năm"
        new_cv["experiences"][0]["description"] = ["Xây dựng giao diện quản trị bằng React và TypeScript cho khách hàng"]
        p = c.post("/match/cv:preview", json={"cv": new_cv, "ref_ym": "2026-11"})
        assert p.status_code == 200, p.text
        pj = p.json()
        assert pj["status"] == "ok" and pj["items"][0]["jd_id"] == "E2E-FE"
        assert len(pj["explanations"]) == len(pj["items"]) and "CV của bạn" in pj["explanations"][0]["text"]
        with svc.connect() as conn:
            after = {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in before}
        assert after == before                                             # khong con du lieu tam
        assert c.get("/health").json()["n_cv"] == len(svc.names)          # CV tam khong vao chi muc
        assert c.get("/health").json()["n_jd_open"] == 3
