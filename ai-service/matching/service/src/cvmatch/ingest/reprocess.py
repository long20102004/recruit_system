"""Chay lai Luong A / B cho toan kho khi KB / ham chuan hoa / model doi (thiet ke 03 "Khi co thay doi").

`cvmatch reprocess cv --from A5|A8|A10` va `cvmatch reprocess jd`.

| --from | Khi nao                                    | Lam gi                                                      |
| A5     | KB co ban chup moi                         | A1-A9 lai; GIU vector cu (doc + gach) - thiet ke: khong can tinh lai |
| A8     | doi ham chuan hoa / mau ghep van ban        | A1-A9 lai; vector tinh lai neu van ban dua vao embed khac    |
| A10    | doi model embedding                         | A1-A9 lai; tinh lai TOAN BO vector                           |

Ban moi ghi SONG SONG (cv_id moi, cung candidate_key / version / content_hash, bo khoa phien ban MOI); ban cu
giu nguyen va van match duoc voi cau hinh cu. Doi `active.yaml` = chuyen CUNG LUC CV lan JD sang phien ban
moi (quy trinh chuyen phien ban day du - danh gia truoc khi chuyen - de T17).
Vector chi dung lai khi CUNG embed_model (khong bao gio so vector cua hai model).

Dau vao la `cv.raw_json` da luu (A1 da adapter + sua ngay): chay lai A1 la idempotent, rieng thong tin
"ngay chi co nam" (`date_year_only`) cua lan nap dau khong con -> `dates_quality` co the thanh `ok`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
import psycopg

from cvmatch.core import events
from cvmatch.core.models import Encoder
from cvmatch.ingest.cv.embed import embed_records
from cvmatch.ingest.cv.write import write_cvs
from cvmatch.ingest.cv.pipeline import build_cv_record
from cvmatch.ingest.cv.record import CvContext

log = logging.getLogger(__name__)
FROM_STEPS = ("A5", "A8", "A10")


@dataclass
class ReprocessReport:
    entity: str
    from_step: str | None
    keys: tuple[str, str, str]
    n_candidates: int = 0
    n_done: int = 0
    n_failed: int = 0
    reused_doc_vectors: int = 0
    reused_bullet_vectors: int = 0
    embedded_texts: int = 0
    errors: list[dict] = field(default_factory=list)
    duration_s: float = 0.0


def _old_vectors(conn, cv_id: str) -> tuple[dict | None, dict[str, np.ndarray]]:
    with conn.cursor(binary=True) as cur:
        cur.execute("SELECT c.doc_text, c.embed_model, v.dense, v.sparse FROM cv c JOIN cv_vector v USING (cv_id)"
                    " WHERE c.cv_id = %s", (cv_id,))
        doc = cur.fetchone()
        cur.execute("SELECT b.context_text, bv.dense FROM cv_bullet b JOIN cv_bullet_vector bv USING (bullet_id)"
                    " WHERE b.cv_id = %s", (cv_id,))
        bul = {r["context_text"]: r["dense"].to_numpy() for r in cur.fetchall()}
    return (dict(doc) if doc else None), bul


def reprocess_cvs(conn: psycopg.Connection, ctx: CvContext, encoder: Encoder, *, from_step: str = "A5",
                  batch_size: int = 32, limit: int | None = None) -> ReprocessReport:
    if from_step not in FROM_STEPS:
        raise ValueError(f"--from phai thuoc {FROM_STEPS}")
    keys = (ctx.snapshot.ontology_version, ctx.cfg.prep.version, encoder.key())
    rep = ReprocessReport("cv", from_step, keys)
    t0 = time.perf_counter()
    # CV dang dung (moi bo khoa cu) chua co ban song song o bo khoa moi
    rows = conn.execute(
        "SELECT c.cv_id::text AS cv_id, c.raw_json, c.content_hash, c.candidate_key, c.version, c.embed_model"
        " FROM cv c WHERE c.status = 'active' AND c.is_latest AND c.raw_json IS NOT NULL"
        " AND (c.ontology_version, c.pipeline_version, c.embed_model) <> (%s, %s, %s)"
        " AND NOT EXISTS (SELECT 1 FROM cv n WHERE n.content_hash = c.content_hash AND n.status = 'active'"
        "   AND n.ontology_version = %s AND n.pipeline_version = %s AND n.embed_model = %s)"
        " ORDER BY c.created_at, c.cv_id", (*keys, *keys)).fetchall()
    if limit:
        rows = rows[:limit]
    rep.n_candidates = len(rows)
    saved = ctx.dedup
    ctx.dedup = None                                       # khong dedup: day la ban song song co chu dich
    try:
        for s in range(0, len(rows), batch_size):
            _batch(conn, ctx, encoder, rows[s:s + batch_size], from_step, rep)
    finally:
        ctx.dedup = saved
    rep.duration_s = round(time.perf_counter() - t0, 3)
    return rep


def _batch(conn, ctx: CvContext, encoder: Encoder, rows: list[dict], from_step: str, rep: ReprocessReport) -> None:
    recs, olds = [], []
    for r in rows:
        try:
            rec = build_cv_record(r["raw_json"], ctx)
        except Exception as e:  # noqa: BLE001 - JSON da luu khong qua A1 cua pipeline moi
            rep.n_failed += 1
            rep.errors.append({"cv_id": r["cv_id"], "error": f"{type(e).__name__}: {e}"})
            continue
        rec.content_hash = r["content_hash"]               # giu dinh danh noi dung cua lan nap goc
        rec.candidate_key = r["candidate_key"]
        rec.version = int(r["version"])
        rec.replaces_cv_id = None
        rec.is_latest = True
        recs.append(rec)
        olds.append(r)
    if not recs:
        return
    same_model = [o["embed_model"] == encoder.key() for o in olds]
    if from_step == "A10" or not any(same_model):
        embed_records(recs, encoder)
        rep.embedded_texts += sum(1 + len(r.bullets) for r in recs)
    else:
        need_doc, need_b = [], []
        for rec, o, same in zip(recs, olds, same_model):
            doc, bul = _old_vectors(conn, o["cv_id"]) if same else (None, {})
            reuse_doc = doc is not None and (from_step == "A5" or doc["doc_text"] == rec.doc_text)
            rec.vectors = {"embed_model": encoder.key(),
                           "doc_dense": doc["dense"].to_numpy().astype(np.float16) if reuse_doc else None,
                           "doc_sparse": doc["sparse"] if reuse_doc else None,
                           "bullet_dense": [bul.get(b.context_text) for b in rec.bullets]}
            rep.reused_doc_vectors += int(reuse_doc)
            if not reuse_doc:
                need_doc.append(rec)
            for k, b in enumerate(rec.bullets):
                if rec.vectors["bullet_dense"][k] is None:
                    need_b.append((rec, k, b.context_text))
                else:
                    rep.reused_bullet_vectors += 1
        if need_doc:
            enc = encoder.encode([r.doc_text or "" for r in need_doc])
            for i, r in enumerate(need_doc):
                r.vectors["doc_dense"] = enc.dense[i].astype(np.float16)
                r.vectors["doc_sparse"] = enc.sparse[i]
        if need_b:
            enc = encoder.encode([t for _, _, t in need_b])
            for i, (r, k, _) in enumerate(need_b):
                r.vectors["bullet_dense"][k] = enc.dense[i]
        rep.embedded_texts += len(need_doc) + len(need_b)
        for r in recs:
            bd = r.vectors["bullet_dense"]
            r.vectors["bullet_dense"] = (np.stack(bd).astype(np.float16) if bd
                                         else np.zeros((0, encoder.dim), np.float16))
    write_cvs(conn, recs)
    for r in recs:
        events.emit("cv_committed", events.CvCommitted(r.cv_id, None))
    rep.n_done += len(recs)


def reprocess_jds(conn: psycopg.Connection, ctx, encoder: Encoder, *, limit: int | None = None) -> ReprocessReport:
    """JD: Luong B lai tren raw_json cua ban moi nhat -> version moi o bo khoa moi (ban cu giu de cau hinh cu
    van chon duoc theo bo khoa). Trang thai tin giu nguyen."""
    from cvmatch.ingest.jd.embed import embed_jd_records
    from cvmatch.ingest.jd.write import write_jd
    from cvmatch.ingest.jd.pipeline import build_jd_record

    keys = (ctx.snapshot.ontology_version, ctx.cfg.prep.version, encoder.key())
    rep = ReprocessReport("jd", None, keys)
    t0 = time.perf_counter()
    rows = conn.execute(
        "SELECT j.jd_id, j.version, j.status, j.raw_json FROM jd j WHERE j.is_latest"
        " AND (j.ontology_version, j.pipeline_version, j.embed_model) <> (%s, %s, %s) ORDER BY j.jd_id",
        keys).fetchall()
    if limit:
        rows = rows[:limit]
    rep.n_candidates = len(rows)
    for r in rows:
        try:
            rec = build_jd_record(r["raw_json"], ctx, None)
            rec.version = int(r["version"]) + 1
            rec.status = r["status"]
            embed_jd_records([rec], encoder)
            write_jd(conn, rec)
            rep.n_done += 1
            rep.embedded_texts += 1 + len(rec.responsibilities)
            events.emit("jd_committed", events.JdCommitted(rec.jd_id, rec.version))
        except Exception as e:  # noqa: BLE001
            rep.n_failed += 1
            rep.errors.append({"jd_id": r["jd_id"], "error": f"{type(e).__name__}: {e}"})
    rep.duration_s = round(time.perf_counter() - t0, 3)
    return rep
