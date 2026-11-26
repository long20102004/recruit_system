"""T05 (phan con thieu): reprocess cv --from A5|A8|A10, reprocess jd - ghi song song, ban cu van match duoc."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.kb.store import import_snapshot
from cvmatch.core.models import FakeEncoder
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.service import CvIngestor, delete_cv
from cvmatch.ingest.jd.pipeline import JdIngestor
from cvmatch.ingest.reprocess import reprocess_cvs, reprocess_jds
from cvmatch.retrieve.jd_to_cvs import retrieve_for_jd
from cvmatch.retrieve.index import CvIndex
from cvmatch.retrieve.jd_index import JdIndex

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
E2E = FIX / "e2e"
K1 = "fake-bge-m3@5617a9f61b"


def _cvs():
    return [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted((E2E / "cv").glob("*.json"))][:8]


def _ctx(snap, key):
    cfg = load_config(overrides={"ontology_version": snap.ontology_version, "models": {"embed": {"key": key}}})
    return cfg, CvContext.create(cfg, snap, hmac_key="k", ingest_ym="2026-11")


@pytest.fixture()
def env(fresh_db_url, tmp_path):
    migrate(fresh_db_url)
    kb2 = tmp_path / "kb2"
    shutil.copytree(FIX / "kb_mini", kb2)
    man = json.loads((kb2 / "manifest.json").read_text(encoding="utf-8"))
    man["ontology_version"] = "kb-mini-test-2"
    (kb2 / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    with connect(fresh_db_url) as conn:
        import_snapshot(conn, FIX / "kb_mini")
        import_snapshot(conn, kb2)
    s1, s2 = KBSnapshot.from_dir(FIX / "kb_mini"), KBSnapshot.from_dir(kb2)
    cfg1, ctx1 = _ctx(s1, K1)
    enc1 = FakeEncoder(key=K1)
    with connect(fresh_db_url) as conn:
        outs = CvIngestor(conn, ctx1, enc1).ingest_many(_cvs())
        jd = json.loads((E2E / "jd" / "e2e-java.json").read_text(encoding="utf-8"))
        assert JdIngestor(conn, ctx1, enc1).ingest_one(copy.deepcopy(jd)).status == "ok"
        yield conn, (cfg1, ctx1, enc1), s2, outs, jd


def test_reprocess_a5_parallel_and_reuse(env):
    conn, (cfg1, ctx1, enc1), s2, outs, jd = env
    cfg2, ctx2 = _ctx(s2, K1)
    rep = reprocess_cvs(conn, ctx2, enc1, from_step="A5")
    assert rep.n_candidates == 8 and rep.n_done == 8 and rep.n_failed == 0
    assert rep.reused_doc_vectors == 8 and rep.embedded_texts == 0         # A5: giu toan bo vector
    # chay lai: khong con gi de lam (idempotent)
    assert reprocess_cvs(conn, ctx2, enc1, from_step="A5").n_candidates == 0
    # ban cu van match duoc voi cau hinh cu; ban moi voi cau hinh moi - cung so CV
    idx1, idx2 = CvIndex(cfg1).build(conn), CvIndex(cfg2).build(conn)
    assert idx1.n_cv == idx2.n_cv == 8 and not set(idx1.cv_ids) & set(idx2.cv_ids)
    r1 = retrieve_for_jd(conn, idx1, cfg1, "E2E-JAVA", write_log=False)
    assert len(r1.items) == 8
    # JD: cau hinh moi chua co JD -> reprocess jd -> ca hai cau hinh deu chon duoc ban cua minh
    assert JdIndex(cfg2).build(conn).n_jd == 0
    rj = reprocess_jds(conn, ctx2, enc1)
    assert rj.n_done == 1
    r2 = retrieve_for_jd(conn, idx2, cfg2, "E2E-JAVA", write_log=False)
    assert r2.jd_version == 2 and len(r2.items) == 8
    assert retrieve_for_jd(conn, idx1, cfg1, "E2E-JAVA", write_log=False).jd_version == 1
    assert JdIndex(cfg1).build(conn).n_jd == JdIndex(cfg2).build(conn).n_jd == 1
    # nap lai dung file goc o cau hinh moi -> duplicate (da co ban o bo khoa moi), khong tao them
    (o,) = CvIngestor(conn, ctx2, enc1).ingest_many(_cvs()[:1])
    assert o.status == "duplicate" and o.cv_id in idx2.cv_ids
    # xoa CV -> xoa ca ban song song
    victim = outs[0].cv_id
    assert delete_cv(conn, victim)
    n = conn.execute("SELECT count(*) AS n FROM cv WHERE status = 'active' AND content_hash ="
                     " (SELECT content_hash FROM cv WHERE cv_id = %s)", (victim,)).fetchone()["n"]
    assert n == 0


def test_reprocess_a10_new_model(env):
    conn, (cfg1, ctx1, enc1), s2, outs, jd = env
    k2 = "fake-other-model@1"
    cfg3, ctx3 = _ctx(KBSnapshot.from_dir(FIX / "kb_mini"), k2)
    enc2 = FakeEncoder(key=k2)
    rep = reprocess_cvs(conn, ctx3, enc2, from_step="A5")          # model khac -> khong dung lai vector du --from A5
    assert rep.n_done == 8 and rep.reused_doc_vectors == 0 and rep.embedded_texts > 8
    models = {r["embed_model"] for r in conn.execute("SELECT DISTINCT embed_model FROM cv_vector")}
    assert models == {K1, k2}
    assert CvIndex(cfg3).build(conn).n_cv == 8 and CvIndex(cfg1).build(conn).n_cv == 8


def test_reprocess_a8_recompute_changed_text(env):
    conn, (cfg1, ctx1, enc1), s2, outs, jd = env
    cfg4 = load_config(overrides={"ontology_version": "kb-mini-test", "models": {"embed": {"key": K1}},
                                  "prep": {"version": "prep-9.9-test"}})
    ctx4 = CvContext.create(cfg4, KBSnapshot.from_dir(FIX / "kb_mini"), hmac_key="k", ingest_ym="2026-11")
    rep = reprocess_cvs(conn, ctx4, enc1, from_step="A8")
    # cung ham chuan hoa -> van ban giong het -> dung lai vector (doc + gach), khong embed lai
    assert rep.n_done == 8 and rep.reused_doc_vectors == 8 and rep.embedded_texts == 0
    assert rep.reused_bullet_vectors > 0
