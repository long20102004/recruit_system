"""T05: A10 + A11 tren Postgres that, voi FakeEncoder."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from cvmatch.core.config import load_config
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.models import FakeEncoder
from cvmatch.core import events
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.service import CvIngestor, delete_cv

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE = json.loads((FIX / "cv" / "cv_sample.json").read_text(encoding="utf-8"))
CV_TABLES = ("cv", "cv_meta", "cv_experience", "cv_education", "cv_skill", "cv_bullet",
             "cv_vector", "cv_bullet_vector", "cv_bm25_doc", "cv_summary_sentence")


@pytest.fixture()
def db(fresh_db_url):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        yield conn


@pytest.fixture()
def ingestor(db):
    ctx = CvContext.create(load_config(), KBSnapshot.from_dir(FIX / "kb_mini"),
                           hmac_key="k", ingest_ym="2026-11")
    return CvIngestor(db, ctx, FakeEncoder(key="fake-bge-m3@5617a9f61b"))


def counts(conn):
    return {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in CV_TABLES}


def test_ingest_sample_fills_all_tables(db, ingestor):
    seen = []
    events.on("cv_committed", seen.append)
    try:
        (o,) = ingestor.ingest_many([("cv_sample.json", copy.deepcopy(SAMPLE))])
    finally:
        events.off("cv_committed", seen.append)
    assert o.status == "ok" and seen and seen[0].cv_id == o.cv_id
    assert counts(db) == {"cv": 1, "cv_meta": 1, "cv_experience": 1, "cv_education": 1, "cv_skill": 5,
                          "cv_bullet": 2, "cv_vector": 1, "cv_bullet_vector": 2, "cv_bm25_doc": 1, "cv_summary_sentence": 1}

    cv = db.execute("SELECT * FROM cv").fetchone()
    assert (cv["status"], cv["is_latest"], cv["version"]) == ("active", True, 1)
    assert (cv["ontology_version"], cv["pipeline_version"], cv["embed_model"]) == \
        ("kb-mini-test", "prep-1.2", "fake-bge-m3@5617a9f61b")
    meta = db.execute("SELECT * FROM cv_meta").fetchone()
    assert float(meta["years_experience"]) == 4.7 and meta["role_group"] == "Backend" and meta["n_bullets"] == 2

    # bullet_id cua cv_skill tro dung gach chua bang chung
    rows = db.execute("SELECT s.skill_id, b.text_raw FROM cv_skill s JOIN cv_bullet b USING (bullet_id)"
                      " ORDER BY s.skill_id").fetchall()
    assert [(r["skill_id"], r["text_raw"]) for r in rows] == [
        ("S0002", "Xây dựng API thanh toán bằng Spring Boot"),
        ("S0015", "Tối ưu truy vấn PostgreSQL, giảm 40% thời gian"),
    ]
    vec = db.execute("SELECT dense FROM cv_vector").fetchone()["dense"]
    assert np.isclose(np.linalg.norm(vec.to_numpy().astype(np.float32)), 1.0, atol=1e-2)
    log = db.execute("SELECT status FROM ingest_log").fetchall()
    assert [r["status"] for r in log] == ["ok"]


def test_duplicate_and_new_version(db, ingestor):
    (o1,) = ingestor.ingest_many([("a", copy.deepcopy(SAMPLE))])
    (o2,) = ingestor.ingest_many([("a-again", copy.deepcopy(SAMPLE))])
    assert o2.status == "duplicate" and o2.cv_id == o1.cv_id
    assert counts(db)["cv"] == 1

    newer = copy.deepcopy(SAMPLE)
    newer["summary"] = "Backend developer 5 năm kinh nghiệm Java"
    (o3,) = ingestor.ingest_many([("b", newer)])
    assert (o3.status, o3.version) == ("ok", 2)
    rows = {str(r["cv_id"]): r["is_latest"] for r in db.execute("SELECT cv_id, is_latest FROM cv")}
    assert rows == {o1.cv_id: False, o3.cv_id: True}


def test_revert_to_old_content_makes_new_version(db, ingestor):
    """V-09: v1 -> v2 -> noi dung v1 lan nua => version 3 moi nhat (khong tra id v1 da cu)."""
    (o1,) = ingestor.ingest_many([("v1", copy.deepcopy(SAMPLE))])
    newer = copy.deepcopy(SAMPLE)
    newer["summary"] = "Backend developer 5 năm kinh nghiệm Java"
    (o2,) = ingestor.ingest_many([("v2", newer)])
    (o3,) = ingestor.ingest_many([("v1-again", copy.deepcopy(SAMPLE))])
    assert (o3.status, o3.version) == ("ok", 3) and o3.cv_id not in (o1.cv_id, o2.cv_id)
    rows = {str(r["cv_id"]): r["is_latest"] for r in db.execute("SELECT cv_id, is_latest FROM cv")}
    assert rows == {o1.cv_id: False, o2.cv_id: False, o3.cv_id: True}
    (o4,) = ingestor.ingest_many([("v1-again-2", copy.deepcopy(SAMPLE))])
    assert o4.status == "duplicate" and o4.cv_id == o3.cv_id


def test_duplicate_within_same_batch(db, ingestor):
    out = ingestor.ingest_many([("x", copy.deepcopy(SAMPLE)), ("y", copy.deepcopy(SAMPLE))])
    assert [o.status for o in out] == ["ok", "duplicate"]


def test_invalid_logged_without_cv_row(db, ingestor):
    bad = copy.deepcopy(SAMPLE)
    bad["experiences"] = "sai kiểu"
    (o,) = ingestor.ingest_many([("bad.json", bad)])
    assert o.status == "invalid"
    assert counts(db)["cv"] == 0
    row = db.execute("SELECT status, errors FROM ingest_log").fetchone()
    assert row["status"] == "invalid" and row["errors"][0]["loc"][0] == "experiences"


def _patch_halfvec(monkeypatch, fail_when):
    import cvmatch.ingest.cv.write as a11

    real = a11.halfvec
    calls = {"n": 0}

    def boom(x):
        calls["n"] += 1
        if fail_when(calls["n"]):  # loi o vector gach thu hai, sau khi da chen cv, meta, gach...
            raise RuntimeError("loi gia lap giua giao dich")
        return real(x)

    monkeypatch.setattr(a11, "halfvec", boom)


def test_failure_mid_write_leaves_nothing(db, ingestor, monkeypatch):
    _patch_halfvec(monkeypatch, lambda n: n >= 2)          # loi mai -> het 3 lan thu
    (o,) = ingestor.ingest_many([("s", copy.deepcopy(SAMPLE))])
    assert o.status == "failed"
    assert all(n == 0 for n in counts(db).values())
    row = db.execute("SELECT status, detail FROM ingest_log").fetchone()
    assert row["status"] == "failed" and row["detail"]["step"] == "A11"


def test_transient_failure_retried_once_written_once(db, ingestor, monkeypatch):
    _patch_halfvec(monkeypatch, lambda n: n == 2)          # chi loi lan dau
    (o,) = ingestor.ingest_many([("s", copy.deepcopy(SAMPLE))])
    assert o.status == "ok"
    assert counts(db) == {"cv": 1, "cv_meta": 1, "cv_experience": 1, "cv_education": 1, "cv_skill": 5,
                          "cv_bullet": 2, "cv_vector": 1, "cv_bullet_vector": 2, "cv_bm25_doc": 1, "cv_summary_sentence": 1}


def test_delete_removes_personal_content(db, ingestor):
    (o,) = ingestor.ingest_many([("s", copy.deepcopy(SAMPLE))])
    seen = []
    events.on("cv_deleted", seen.append)
    try:
        assert delete_cv(db, o.cv_id)
    finally:
        events.off("cv_deleted", seen.append)
    cv = db.execute("SELECT status, is_latest, raw_json, anon_json, doc_text FROM cv").fetchone()
    assert (cv["status"], cv["is_latest"], cv["raw_json"], cv["anon_json"], cv["doc_text"]) == \
        ("deleted", False, None, None, None)
    c = counts(db)
    assert c["cv_bullet"] == c["cv_bullet_vector"] == c["cv_vector"] == c["cv_bm25_doc"] == 0
    assert db.execute("SELECT count(*) AS n FROM cv_skill WHERE evidence_snippet IS NOT NULL").fetchone()["n"] == 0
    # 2 gach + 1 cau summary (prep-1.1) -> cache BERTScore xoa ca ba
    assert seen and len(seen[0].bullet_texts_raw) == 3
    assert c["cv_summary_sentence"] == 0
    # nap lai sau khi xoa: khong bi coi la trung
    (o2,) = ingestor.ingest_many([("s2", copy.deepcopy(SAMPLE))])
    assert o2.status == "ok"


def test_cli_ingest_dir(fresh_db_url, tmp_path, monkeypatch):
    from cvmatch.cli import main

    migrate(fresh_db_url)
    (tmp_path / "a.json").write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{không phải json", encoding="utf-8")
    monkeypatch.setenv("CVMATCH_HMAC_KEY", "k")
    rc = main(["ingest", "cv", str(tmp_path), "--kb-dir", str(FIX / "kb_mini"), "--fake-encoder",
               "--url", fresh_db_url, "--ingest-ym", "2026-11"])
    assert rc == 1  # co mot file invalid
    with connect(fresh_db_url) as conn:
        st = sorted(r["status"] for r in conn.execute("SELECT status FROM ingest_log"))
    assert st == ["invalid", "ok"]


def _built(ingestor, raw):
    from cvmatch.core.models import FakeEncoder as FE
    from cvmatch.ingest.cv.embed import embed_records
    from cvmatch.ingest.cv.pipeline import build_cv_record

    ingestor.ctx.dedup = None
    rec = build_cv_record(raw, ingestor.ctx)
    embed_records([rec], FE())
    return rec


def test_write_cvs_batch_is_atomic(db, ingestor):
    from cvmatch.ingest.cv.write import write_cvs

    good = _built(ingestor, copy.deepcopy(SAMPLE))
    other = copy.deepcopy(SAMPLE)
    other["email"] = "b@x.vn"
    bad = _built(ingestor, other)
    bad.meta.level_rank = 9  # vi pham CHECK -> ca lo rollback
    with pytest.raises(Exception):
        write_cvs(db, [good, bad])
    assert all(n == 0 for n in counts(db).values())


def test_two_versions_same_person_in_one_batch(db, ingestor):
    v2 = copy.deepcopy(SAMPLE)
    v2["summary"] = "Backend developer 5 năm kinh nghiệm Java"
    out = ingestor.ingest_many([("v1", copy.deepcopy(SAMPLE)), ("v2", v2)])
    assert [(o.status, o.version) for o in out] == [("ok", 1), ("ok", 2)]
    latest = {r["version"]: r["is_latest"] for r in db.execute("SELECT version, is_latest FROM cv")}
    assert latest == {1: False, 2: True}


def test_unknown_skill_counted_across_batch(db, ingestor):
    a = copy.deepcopy(SAMPLE); a["skills"] = ["Figma"]
    b = copy.deepcopy(SAMPLE); b["skills"] = ["Figma"]; b["email"] = "b@x.vn"
    ingestor.ingest_many([("a", a), ("b", b)])
    row = db.execute("SELECT count, sources FROM unknown_skill WHERE text = 'figma'").fetchone()
    assert (row["count"], row["sources"]) == (2, ["cv"])


def test_committed_visible_to_other_connection_before_close(fresh_db_url):
    """Hoi quy: A11 phai COMMIT that (khong phai savepoint trong giao dich ngam do SELECT mo)."""
    migrate(fresh_db_url)
    ctx = CvContext.create(load_config(), KBSnapshot.from_dir(FIX / "kb_mini"), hmac_key="k", ingest_ym="2026-11")
    seen = []

    def check(ev):
        with connect(fresh_db_url) as other:  # ket noi KHAC, ngay luc su kien phat
            seen.append(other.execute("SELECT count(*) AS n FROM cv WHERE cv_id = %s", (ev.cv_id,)).fetchone()["n"])

    events.on("cv_committed", check)
    try:
        with connect(fresh_db_url) as conn:
            CvIngestor(conn, ctx, FakeEncoder()).ingest_many([("a", copy.deepcopy(SAMPLE))])
            assert seen == [1]
    finally:
        events.off("cv_committed", check)
