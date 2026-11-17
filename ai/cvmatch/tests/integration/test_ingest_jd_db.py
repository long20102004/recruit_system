"""T06 tren Postgres that + moc sau T06: nap CV mau + JD mau -> du 17 bang tien xu ly co du lieu."""

import copy
import json
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.models import FakeEncoder
from cvmatch.core import events
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.service import CvIngestor
from cvmatch.ingest.jd.pipeline import JdIngestor, set_jd_status

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
JD = json.loads((FIX / "jd" / "jd_sample.json").read_text(encoding="utf-8"))
CV = json.loads((FIX / "cv" / "cv_sample.json").read_text(encoding="utf-8"))
PREP_TABLES = ("cv", "cv_meta", "cv_experience", "cv_education", "cv_skill", "cv_bullet", "cv_vector",
               "cv_bullet_vector", "cv_bm25_doc", "jd", "jd_meta", "jd_skill", "jd_responsibility",
               "jd_requirement_item", "jd_vector", "unknown_skill", "ingest_log")


@pytest.fixture()
def env(fresh_db_url):
    migrate(fresh_db_url)
    ctx = CvContext.create(load_config(), KBSnapshot.from_dir(FIX / "kb_mini"), hmac_key="k", ingest_ym="2026-11")
    enc = FakeEncoder(key="fake-bge-m3@5617a9f61b")
    with connect(fresh_db_url) as conn:
        yield conn, ctx, enc


def n(conn, table, where="true"):
    return conn.execute(f"SELECT count(*) AS n FROM {table} WHERE {where}").fetchone()["n"]


def test_ingest_jd_sample(env):
    conn, ctx, enc = env
    o = JdIngestor(conn, ctx, enc).ingest_one(copy.deepcopy(JD))
    assert (o.status, o.jd_id, o.version, o.warnings) == ("ok", "JD-0412", 1, [])
    assert {t: n(conn, t) for t in ("jd", "jd_meta", "jd_skill", "jd_responsibility", "jd_requirement_item",
                                    "jd_vector")} == \
        {"jd": 1, "jd_meta": 1, "jd_skill": 5, "jd_responsibility": 3, "jd_requirement_item": 2, "jd_vector": 1}
    row = conn.execute("SELECT * FROM jd").fetchone()
    assert (row["status"], row["is_latest"], row["warnings"]) == ("open", True, [])
    assert n(conn, "jd_responsibility", "dense IS NOT NULL") == 3
    meta = conn.execute("SELECT * FROM jd_meta").fetchone()
    assert (meta["location"], float(meta["min_years"]), meta["level_rank"], meta["role_group"]) == \
        ("ho_chi_minh", 4.0, 4, "Backend")


def test_jd_new_version_unchanged_and_status(env):
    conn, ctx, enc = env
    ing = JdIngestor(conn, ctx, enc)
    assert ing.ingest_one(copy.deepcopy(JD)).version == 1
    assert ing.ingest_one(copy.deepcopy(JD)).status == "unchanged"
    edited = copy.deepcopy(JD)
    edited["min_years"] = 5
    assert ing.ingest_one(edited).version == 2
    assert [(r["version"], r["is_latest"]) for r in conn.execute("SELECT version, is_latest FROM jd ORDER BY version")] \
        == [(1, False), (2, True)]

    seen = []
    events.on("jd_status_changed", seen.append)
    try:
        assert set_jd_status(conn, "JD-0412", "closed") == 2
    finally:
        events.off("jd_status_changed", seen.append)
    assert n(conn, "jd", "status = 'closed'") == 1 and n(conn, "jd") == 2   # khong tao version moi
    assert seen[0].status == "closed"


def test_jd_invalid_logged(env):
    conn, ctx, enc = env
    o = JdIngestor(conn, ctx, enc).ingest_one({"jd_id": "BAD", "title": "Dev"})
    assert o.status == "invalid" and n(conn, "jd") == 0
    assert conn.execute("SELECT status, entity_id FROM ingest_log").fetchone() == {"status": "invalid", "entity_id": "BAD"}


def test_milestone_all_17_prep_tables(env):
    """Moc sau T06 (ke hoach 00): nap CV + JD mau, du 17 bang tien xu ly co du lieu."""
    conn, ctx, enc = env
    cv = copy.deepcopy(CV)
    cv["skills"].append("Figma")   # de unknown_skill co dong
    assert CvIngestor(conn, ctx, enc).ingest_one(cv).status == "ok"
    assert JdIngestor(conn, ctx, enc).ingest_one(copy.deepcopy(JD)).status == "ok"
    empty = [t for t in PREP_TABLES if n(conn, t) == 0]
    assert empty == []
    # CV va JD cung bo phien ban -> so duoc voi nhau (thiet ke 00 muc 3.4)
    v_cv = conn.execute("SELECT ontology_version, pipeline_version, embed_model FROM cv").fetchone()
    v_jd = conn.execute("SELECT ontology_version, pipeline_version, embed_model FROM jd").fetchone()
    assert v_cv == v_jd
