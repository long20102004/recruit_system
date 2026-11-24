"""T13: API (TestClient) va run-e2e tren Postgres that, FakeEncoder + KB mini."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cvmatch.api.app import create_app
from cvmatch.api.e2e import run_e2e
from cvmatch.api.services import Services, config_and_encoder
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.store import import_snapshot

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
E2E = FIX / "e2e"


def _load(d: Path) -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))]


@pytest.fixture()
def client(fresh_db_url):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        version = import_snapshot(conn, FIX / "kb_mini")
    cfg, enc = config_and_encoder(fake=True, overrides={"ontology_version": version})
    with Services(cfg, url=fresh_db_url, encoder=enc, hmac_key="k") as svc:
        with TestClient(create_app(svc)) as c:
            yield c, svc, fresh_db_url


def test_ingest_match_explain(client):
    c, svc, url = client
    h = c.get("/health").json()
    assert h["status"] == "ok" and h["versions"]["embed_model"].startswith("fake-") and h["n_cv"] == 0
    cvs = _load(E2E / "cv")
    ids = []
    for cv in cvs[:20]:                                           # nap tung CV: index tang dan qua su kien
        r = c.post("/cv", json=cv)
        assert r.status_code == 200 and r.json()["status"] == "ok", r.text
        ids.append(r.json()["cv_id"])
    dup = c.post("/cv", json=cvs[0]).json()
    assert dup["status"] == "duplicate" and dup["cv_id"] == ids[0]
    job = c.post("/cv/batch", json={"items": cvs[20:]})          # lo chay nen
    assert job.status_code == 202
    c.app.state.jobs.wait_all()
    j = c.get(f"/jobs/{job.json()['job_id']}").json()
    assert j["status"] == "done" and all(x["status"] == "ok" for x in j["result"]["results"])
    assert c.get("/health").json()["n_cv"] == len(cvs)

    bad = c.post("/cv", json={"experiences": "x"})
    assert bad.status_code == 422 and bad.json()["status"] == "invalid"

    jd = _load(E2E / "jd")
    java = next(x for x in jd if x["jd_id"] == "E2E-JAVA")
    r = c.post("/jd", json=java)
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["version"] == 1
    assert c.post("/jd", json=java).json()["status"] == "unchanged"

    m = c.post("/match/jd/E2E-JAVA", json={"N": 10, "ref_ym": "2026-11"})
    assert m.status_code == 200, m.text
    body = m.json()
    assert len(body["items"]) == 10 and body["n_pool"] == len(cvs)
    assert [it["rank"] for it in body["items"]] == list(range(1, 11))
    assert all(set(it) == {"cv_id", "rank", "score", "band", "cap_applied", "flags", "features", "skills"}
               for it in body["items"])
    it0 = body["items"][0]
    assert set(it0["features"]) == {"A1", "A2", "B4", "B5", "B1", "B2", "B3", "C1"}
    assert it0["features"]["A1"] is not None and 0 <= it0["features"]["A1"] <= 1
    assert set(it0["skills"]) == {"met", "partial", "missing"} and it0["skills"]["met"]
    assert body["items"][0]["score"] >= body["items"][-1]["score"]
    assert {"retrieve_s", "rerank_s"} <= set(body["timings"])

    top = body["items"][0]["cv_id"]
    e = c.get(f"/match/{body['run_id']}/cv/{top}/explain")
    assert e.status_code == 200 and e.json()["cv_id"] == top and e.json()["text"].startswith("Điểm")
    assert c.get(f"/match/{body['run_id']}/cv/{top}/explain").json()["cache_key"] == e.json()["cache_key"]

    # khoa phien ban + config_json day du o match_run / rerank_run
    with connect(url) as conn:
        mr = conn.execute("SELECT * FROM match_run WHERE run_id = %s", (body["retrieve_run_id"],)).fetchone()
        rr = conn.execute("SELECT * FROM rerank_run WHERE run_id = %s", (body["run_id"],)).fetchone()
    v = h["versions"]
    assert (mr["ontology_version"], mr["pipeline_version"], mr["embed_model"]) == (
        v["ontology_version"], v["pipeline_version"], v["embed_model"])
    assert mr["config_json"]["rerank"]["version"] == "rr-1.0" and mr["config_hash"]
    assert rr["config_json"]["versions"] == v and rr["bertscore_config"] == v["bertscore_config"]
    assert rr["config_json"]["bertscore"]["layer"] == 24 and rr["rerank_config_version"] == "rr-1.0"

    # loc dia diem: chuoi nguoi dung nhap ("Hồ Chí Minh") phai doi ve cung ma voi cv_meta.location
    lf = c.post("/match/jd/E2E-JAVA", json={"hard_filters": {"location": "Hồ Chí Minh", "allow_remote": False}}).json()
    assert 0 < lf["n_pool"] < len(cvs)

    # loai tru + xoa CV + chay nen
    m2 = c.post("/match/jd/E2E-JAVA", json={"N": 5, "exclude_cv_ids": [top], "background": True})
    assert m2.status_code == 202
    c.app.state.jobs.wait_all()
    res = c.get(f"/jobs/{m2.json()['job_id']}").json()
    assert res["status"] == "done" and top not in [x["cv_id"] for x in res["result"]["items"]]
    assert c.delete(f"/cv/{top}").json() == {"cv_id": top, "deleted": True}
    assert c.delete(f"/cv/{top}").status_code == 404                # xoa lan 2
    assert c.get("/health").json()["n_cv"] == len(cvs) - 1
    m3 = c.post("/match/jd/E2E-JAVA", json={"N": 50}).json()
    assert top not in [x["cv_id"] for x in m3["items"]]

    assert c.patch("/jd/E2E-JAVA/status", json={"status": "closed"}).json() == {
        "jd_id": "E2E-JAVA", "version": 1, "status": "closed"}
    assert c.patch("/jd/NOPE/status", json={"status": "closed"}).status_code == 404
    assert c.post("/match/jd/NOPE").status_code == 404
    assert c.get(f"/match/{body['run_id']}/cv/00000000-0000-0000-0000-000000000000/explain").status_code == 404
    assert c.get("/jobs/xyz").status_code == 404
    assert "/match/jd/{jd_id}" in c.get("/openapi.json").json()["paths"]


def test_run_e2e(fresh_db_url, tmp_path):
    s = run_e2e(E2E / "cv", E2E / "jd", url=fresh_db_url, kb_dir=FIX / "kb_mini", fake=True, out_dir=tmp_path,
                ref_ym="2026-11", hmac_key="k")
    assert s["cv_status"] == {"ok": 34} and [j["status"] for j in s["jd_status"]] == ["ok"] * 3
    assert len(s["runs"]) == 3 and all(r["status"] == "ok" for r in s["runs"])
    for r in s["runs"]:
        # kho rong luc khoi dong -> BM25 phai duoc dung lai sau lo nap, khong thi moi diem bm25 = 0
        assert max(x["s"]["bm25"] or 0 for x in r["retrieve_top"]) > 0
        assert len(r["explanations"]) == 5 and len(r["retrieve_top"]) == 30 and len(r["rerank_top"]) == 30
    run_dir = Path(s["dir"])
    assert (run_dir / "report.md").exists() and (run_dir / "summary.json").exists()
    log = [json.loads(x) for x in Path(s["log"]).read_text(encoding="utf-8").splitlines()]
    events = [x["event"] for x in log]
    assert events.count("match") == 3 and events.count("explain") == 15 and events[-1] == "e2e_done"
    run_ids = {r["run_id"] for r in s["runs"]}
    assert {x["run_id"] for x in log if x["event"] == "explain"} == run_ids

    # so tay: JD Java -> top 3 la CV java; JD FE -> top la frontend/fullstack; JD Data -> top la data
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "R-A0" in report
    by_jd = {r["jd_id"]: r for r in s["runs"]}

    def roles(jd_id, n):   # cv_00_java.json -> java
        return [s["cv_sources"][it["cv_id"]].split("_")[2].removesuffix(".json")
                for it in by_jd[jd_id]["rerank_top"][:n]]

    assert set(roles("E2E-JAVA", 3)) == {"java"}
    assert set(roles("E2E-FE", 3)) <= {"frontend", "fullstack"}
    assert set(roles("E2E-DATA", 3)) == {"data"}

    # chay lai cung DB: CV duplicate, JD unchanged, van ra ket qua
    s2 = run_e2e(E2E / "cv", E2E / "jd" / "e2e-java.json", url=fresh_db_url, kb_dir=FIX / "kb_mini", fake=True,
                 out_dir=tmp_path / "2", ref_ym="2026-11", hmac_key="k")
    assert s2["cv_status"] == {"duplicate": 34} and s2["jd_status"][0]["status"] == "unchanged"
    assert s2["runs"][0]["status"] == "ok"


def test_include_filters(client):
    """I01: include_cv_ids / include_jd_ids gioi han pool (ung vien da nop don, cham mot cap)."""
    c, svc, url = client
    cvs = _load(E2E / "cv")
    r = c.post("/cv/batch", json={"items": cvs, "background": False})
    ids = [x["cv_id"] for x in r.json()["results"]]
    for jd in _load(E2E / "jd"):
        assert c.post("/jd", json=jd).json()["status"] == "ok"

    pick = ids[:3]
    m = c.post("/match/jd/E2E-JAVA", json={"include_cv_ids": pick + ["00000000-0000-0000-0000-000000000000"]}).json()
    assert m["n_pool"] == 3 and {x["cv_id"] for x in m["items"]} == set(pick)
    assert any(w["code"] == "include_unknown" for w in m["warnings"])
    one = c.post("/match/jd/E2E-JAVA", json={"include_cv_ids": [ids[5]], "N": 1}).json()
    assert [x["cv_id"] for x in one["items"]] == [ids[5]]
    empty = c.post("/match/jd/E2E-JAVA", json={"include_cv_ids": []}).json()
    assert empty["n_pool"] == 0 and empty["items"] == []

    d = c.post(f"/match/cv/{ids[0]}", json={"include_jd_ids": ["E2E-FE"]}).json()
    assert [x["jd_id"] for x in d["items"]] == ["E2E-FE"] and "features" in d["items"][0]
    c.patch("/jd/E2E-DATA/status", json={"status": "closed"})
    d2 = c.post(f"/match/cv/{ids[0]}", json={"include_jd_ids": ["E2E-DATA"]}).json()
    assert d2["items"] == [] and any(w["code"] == "include_unknown" for w in d2["warnings"])


def test_service_token(fresh_db_url):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        version = import_snapshot(conn, FIX / "kb_mini")
    cfg, enc = config_and_encoder(fake=True, overrides={"ontology_version": version})
    with Services(cfg, url=fresh_db_url, encoder=enc, hmac_key="k") as svc:
        with TestClient(create_app(svc, token="s3cret")) as c:
            assert c.get("/health").status_code == 200                       # mo
            assert c.post("/jd/X/status").status_code == 401
            assert c.get("/openapi.json").status_code == 401
            assert c.patch("/jd/X/status", json={"status": "closed"},
                           headers={"X-Service-Token": "wrong"}).status_code == 401
            assert c.patch("/jd/X/status", json={"status": "closed"},
                           headers={"X-Service-Token": "s3cret"}).status_code == 404
    with pytest.raises(RuntimeError):
        create_app(svc, token="", env="prod")
