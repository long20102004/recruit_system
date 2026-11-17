"""T08: CvIndex dung tu Postgres, cap nhat tang dan, kiem nhat quan."""

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
from cvmatch.ingest.cv.service import CvIngestor, delete_cv
from cvmatch.retrieve.index import CvIndex

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE = json.loads((FIX / "cv" / "cv_sample.json").read_text(encoding="utf-8"))
KEY = "fake-bge-m3@5617a9f61b"


def make_cv(i, bullets):
    d = copy.deepcopy(SAMPLE)
    d["email"] = f"u{i}@x.vn"
    d["experiences"][0]["description"] = bullets
    return d


@pytest.fixture()
def env(fresh_db_url):
    migrate(fresh_db_url)
    snap = KBSnapshot.from_dir(FIX / "kb_mini")
    cfg = load_config(overrides={"ontology_version": snap.ontology_version, "models": {"embed": {"key": KEY}}})
    ctx = CvContext.create(cfg, snap, hmac_key="k", ingest_ym="2026-11")
    with connect(fresh_db_url) as conn:
        ing = CvIngestor(conn, ctx, FakeEncoder(key=KEY))
        yield conn, cfg, ing, fresh_db_url


def test_build_shapes_and_alignment(env):
    conn, cfg, ing, _ = env
    outs = ing.ingest_many([(str(i), make_cv(i, [f"Xây dựng API thanh toán số {j} bằng Spring Boot"
                                                 for j in range(i + 1)])) for i in range(4)])
    idx = CvIndex(cfg).build(conn)
    assert idx.n_cv == 4 and idx.doc_matrix.shape == (4, 1024) and idx.doc_matrix.dtype == np.float16
    assert len(idx.bullet_ids) == 1 + 2 + 3 + 4 and idx.bullets_sorted_by_cv()
    # bullet_cv_index tro dung CV so huu gach
    owner = {int(r["bullet_id"]): str(r["cv_id"]) for r in conn.execute("SELECT bullet_id, cv_id FROM cv_bullet")}
    assert all(idx.cv_ids[i] == owner[b] for i, b in zip(idx.bullet_cv_index, idx.bullet_ids))
    # ma tran ky nang: moi CV co Spring Boot (S0002) voi ev = 1.0 (trong mo ta)
    col = idx.skill_col["S0002"]
    assert np.allclose(idx.skill_matrix[:, col].toarray().ravel(), 1.0)
    assert idx.bm25.n_docs == 4
    assert np.allclose(np.linalg.norm(idx.doc_matrix.astype(np.float32), axis=1), 1, atol=1e-2)
    assert idx.verify(conn) == []
    assert {o.cv_id for o in outs} == set(idx.cv_ids)


def test_versions_filter(env):
    conn, cfg, ing, _ = env
    ing.ingest_many([("a", make_cv(1, ["Xây dựng API thanh toán bằng Spring Boot"]))])
    other = CvIndex(load_config(overrides={"ontology_version": "kb-khac", "models": {"embed": {"key": KEY}}}))
    assert other.build(conn).n_cv == 0        # khac ontology_version -> khong so voi nhau


def test_incremental_add_deactivate_and_verify(env):
    conn, cfg, ing, url = env
    ing.ingest_many([("a", make_cv(1, ["Xây dựng API thanh toán bằng Spring Boot"]))])
    idx = CvIndex(cfg).build(conn)
    idx.attach_events(lambda: connect(url))
    try:
        newer = make_cv(1, ["Tối ưu truy vấn PostgreSQL cho hệ thống lớn", "Viết test tự động cho API"])
        newer["summary"] = "đổi nội dung"
        (o2,) = ing.ingest_many([("a2", newer)])             # ban moi cung nguoi -> ban cu bi tat
        assert idx.n_cv == 2 and int(idx.active.sum()) == 1
        assert idx.active[idx.row_of[o2.cv_id]]
        assert idx.skill_matrix.shape[0] == 2 and "S0015" in idx.skill_col
        assert idx.bm25.n_docs == 2 and idx.bm25.scores(["postgresql"])[idx.row_of[o2.cv_id]] > 0
        assert idx.verify(conn) == []
        delete_cv(conn, o2.cv_id)                             # su kien cv_deleted -> go khoi RAM
        assert int(idx.active.sum()) == 0
    finally:
        from cvmatch.core import events
        events._HANDLERS.clear()


def test_verify_detects_drift(env):
    conn, cfg, ing, _ = env
    (o,) = ing.ingest_many([("a", make_cv(1, ["Xây dựng API thanh toán bằng Spring Boot"]))])
    idx = CvIndex(cfg).build(conn)
    with conn.transaction():
        conn.execute("UPDATE cv SET status = 'deleted' WHERE cv_id = %s", (o.cv_id,))
    assert idx.verify(conn)  # RAM con CV ma Postgres da xoa
