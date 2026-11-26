"""S05: tinh san token BERTScore khi nap / luc khoi dong (V-12), khoa doc-ghi (V-11), dung lai BM25 (V-13)."""

import json
import threading
import time
from pathlib import Path

import pytest

from cvmatch.api.rwlock import RWLock
from cvmatch.api.services import Services, config_and_encoder
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.store import import_snapshot

FIX = Path(__file__).resolve().parents[1] / "fixtures"
E2E = FIX / "e2e"


def _load(d: Path) -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))]


def _svc(url, **kw):
    migrate(url)
    with connect(url) as conn:
        version = import_snapshot(conn, FIX / "kb_mini")
    cfg, enc = config_and_encoder(fake=True, overrides={"ontology_version": version})
    return Services(cfg, url=url, encoder=enc, hmac_key="k", **kw)


def _n_cache(url) -> int:
    with connect(url) as conn:
        return conn.execute("SELECT count(*) AS n FROM bertscore_token_cache").fetchone()["n"]


def test_precompute_on_ingest(fresh_db_url):
    with _svc(fresh_db_url) as svc:
        svc.ingest_cvs([(f"cv{i}", cv) for i, cv in enumerate(_load(E2E / "cv")[:5])])
        n_cv = _n_cache(fresh_db_url)
        assert n_cv > 0
        jd = _load(E2E / "jd")[0]
        assert svc.ingest_jd(jd).status == "ok"
        assert _n_cache(fresh_db_url) > n_cv
        # match ngay sau nap: moi van ban da co trong cache -> khong tinh them
        miss0 = svc.scorer.cache.misses
        svc.match_jd(jd["jd_id"])
        assert svc.scorer.cache.misses == miss0


def test_no_precompute_when_disabled(fresh_db_url):
    with _svc(fresh_db_url, precompute_tokens=False) as svc:
        svc.ingest_cvs([("cv0", _load(E2E / "cv")[0])])
        assert _n_cache(fresh_db_url) == 0
        st = svc.warm_cache(max_s=60)                  # luc khoi dong: lam nong bu
        assert st["state"] == "done" and st["texts"] > 0 and _n_cache(fresh_db_url) > 0


def test_bm25_rebuilt_after_many_deletes(fresh_db_url):
    with _svc(fresh_db_url) as svc:
        out = svc.ingest_cvs([(f"cv{i}", cv) for i, cv in enumerate(_load(E2E / "cv")[:20])])
        t0 = svc._bm25_built_at
        svc.delete_cv(out[0].cv_id)                     # 1/20 = 5 % < 10 %: chua dung lai
        assert svc._bm25_built_at == t0
        for o in out[1:5]:                              # 25 % kho bi xoa -> dung lai IDF
            svc.delete_cv(o.cv_id)
        assert svc._bm25_built_at > t0 and svc._bm25_active_at_build <= 18


# ------------------------------------------------------------------ khoa doc - ghi


def test_rwlock_readers_run_together():
    lock, inside, peak = RWLock(), [0], [0]
    gate = threading.Barrier(4)

    def reader():
        with lock.read():
            inside[0] += 1
            peak[0] = max(peak[0], inside[0])
            gate.wait(timeout=5)
            inside[0] -= 1

    ts = [threading.Thread(target=reader) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    assert peak[0] == 4


def test_rwlock_writer_exclusive_and_reentrant():
    lock, log = RWLock(), []

    def writer():
        with lock.write():
            with lock.read():                           # giu ghi roi doc (preview_cv -> match_cv)
                log.append("w")
                time.sleep(0.05)

    def reader():
        time.sleep(0.01)
        with lock.read():
            log.append("r")

    ts = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    assert log == ["w", "r"]


def test_rwlock_reader_cannot_upgrade():
    lock = RWLock()
    with lock.read(), pytest.raises(RuntimeError):
        with lock.write():
            pass


# ------------------------------------------------------------------ S06: HR xem nguoi da nop


def test_applicant_pool_fully_scored_and_pool_independent(fresh_db_url):
    """V-20 + V-04: pool nguoi nop (34 > N = 30) -> tra du 34; diem tung cap bang diem cham le cap do."""
    with _svc(fresh_db_url) as svc:
        out = svc.ingest_cvs([(f"cv{i}", cv) for i, cv in enumerate(_load(E2E / "cv"))])
        ids = [o.cv_id for o in out if o.status == "ok"]
        jd = _load(E2E / "jd")[0]
        svc.ingest_jd(jd)
        assert svc.cfg.retrieve.pool_rerank_all_max >= len(ids) > svc.cfg.rerank.N
        m = svc.match_jd(jd["jd_id"], N=svc.cfg.rerank.N, include_cv_ids=ids)
        assert len(m.items) == len(ids)
        by = {it["cv_id"]: it["score"] for it in m.items}
        for cv in ids[:8]:
            one = svc.match_jd(jd["jd_id"], include_cv_ids=[cv], N=1)
            assert one.items[0]["score"] == by[cv]


def test_bank_search_keeps_top_n(fresh_db_url):
    """Khong co include_cv_ids (admin xet ca kho) -> van top N nhu cu."""
    with _svc(fresh_db_url) as svc:
        svc.ingest_cvs([(f"cv{i}", cv) for i, cv in enumerate(_load(E2E / "cv"))])
        jd = _load(E2E / "jd")[0]
        svc.ingest_jd(jd)
        assert len(svc.match_jd(jd["jd_id"]).items) == svc.cfg.rerank.N


# ------------------------------------------------------------------ S07: goi y khi co tin moi


def test_recommendable_flag_filter_and_min_score(fresh_db_url):
    from fastapi.testclient import TestClient

    from cvmatch.api.app import create_app

    with _svc(fresh_db_url) as svc, TestClient(create_app(svc)) as c:
        cvs = _load(E2E / "cv")
        out = svc.ingest_cvs([(f"cv{i}", cv) for i, cv in enumerate(cvs)])
        ids = [o.cv_id for o in out]
        jd = _load(E2E / "jd")[0]
        svc.ingest_jd(jd)
        on = ids[:6]
        for cv in on:
            r = c.patch(f"/cv/{cv}", json={"recommendable": True})
            assert r.status_code == 200 and cv in r.json()["cv_ids"]
        assert c.patch("/cv/00000000-0000-0000-0000-000000000000", json={"recommendable": True}).status_code == 404

        r = c.post(f"/match/jd/{jd['jd_id']}", json={"only_recommendable": True}).json()
        assert {it["cv_id"] for it in r["items"]} <= set(on) and r["n_pool"] == 6
        full = {it["cv_id"]: it["score"] for it in r["items"]}
        thr = sorted(full.values())[len(full) // 2]
        r2 = c.post(f"/match/jd/{jd['jd_id']}", json={"only_recommendable": True, "min_score": thr}).json()
        assert r2["items"] and all(it["score"] >= thr for it in r2["items"])
        # diem trong goi y = diem khi ung vien mo tin (cham le, chieu JD -> CV)
        cv0 = r["items"][0]["cv_id"]
        assert svc.match_jd(jd["jd_id"], include_cv_ids=[cv0], N=1).items[0]["score"] == full[cv0]

        # ban CV moi cua cung nguoi ke thua co; tat co -> ra khoi pool
        newer = dict(cvs[0])
        newer["summary"] = (newer.get("summary") or "") + " Cap nhat CV."
        (o,) = svc.ingest_cvs([("cv0-v2", newer)])
        assert o.status == "ok" and svc.index.recommendable[svc.index.row_of[o.cv_id]]
        c.patch(f"/cv/{o.cv_id}", json={"recommendable": False})
        r3 = c.post(f"/match/jd/{jd['jd_id']}", json={"only_recommendable": True}).json()
        assert o.cv_id not in {it["cv_id"] for it in r3["items"]} and r3["n_pool"] == 5
