"""Nap CV theo lo: A1-A9 (thuan) -> A10 (embedding ca lo) -> A11 (moi CV mot giao dich).

Xu ly loi (thiet ke 03 "Loi thuong gap"):
- sai schema (A1) -> ingest_log 'invalid' ngay, khong tao dong `cv`;
- trung hash (A2) -> ingest_log 'duplicate' (kem cv_id ban da co);
- embedding / ghi loi -> thu lai toi da 3 lan, roi ingest_log 'failed'; KHONG co dong nao cua CV
  do trong cac bang (giao dich da rollback).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import psycopg

from cvmatch.core.models import Encoder
from cvmatch.core import events
from cvmatch.ingest.common.writer import log_ingest, log_ingest_now, with_retry
from cvmatch.ingest.cv.a10_embed import embed_records
from cvmatch.ingest.cv.a11_write import write_cv, write_cvs
from cvmatch.ingest.cv.dedup_pg import BatchDedup, PgDedup
from cvmatch.ingest.cv.pipeline import build_cv_record
from cvmatch.ingest.cv.record import CvContext, CvRecord, DuplicateCV
from cvmatch.ingest.cv.schema import InvalidCV

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


@dataclass
class IngestOutcome:
    source: str                        # ten file / vi tri trong lo
    status: str                        # ok | invalid | duplicate | failed
    cv_id: str | None = None
    version: int | None = None
    flags: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)


class CvIngestor:
    def __init__(self, conn: psycopg.Connection, ctx: CvContext, encoder: Encoder, *, batch_size: int = 32):
        self.conn = conn
        self.ctx = ctx
        self.encoder = encoder
        self.batch_size = batch_size

    def ingest_many(self, items: list[tuple[str, Any]]) -> list[IngestOutcome]:
        """`items`: danh sach (ten nguon, CV JSON). Tra ve ket qua theo dung thu tu."""
        out: list[IngestOutcome] = []
        for s in range(0, len(items), self.batch_size):
            out.extend(self._batch(items[s:s + self.batch_size]))
        return out

    def ingest_one(self, raw: Any, source: str = "api") -> IngestOutcome:
        return self.ingest_many([(source, raw)])[0]

    # ----------------------------------------------------------------- noi bo

    def _batch(self, items: list[tuple[str, Any]]) -> list[IngestOutcome]:
        dedup = BatchDedup(PgDedup(self.conn))
        self.ctx.dedup = dedup
        outcomes: list[IngestOutcome | None] = [None] * len(items)
        ready: list[tuple[int, CvRecord, float]] = []

        for i, (src, raw) in enumerate(items):
            t0 = time.perf_counter()
            try:
                rec = build_cv_record(raw, self.ctx)
            except InvalidCV as e:
                log_ingest_now(self.conn, "cv", None, "invalid", errors=e.errors, detail={"source": src})
                outcomes[i] = IngestOutcome(src, "invalid", detail={"errors": e.errors})
                continue
            except DuplicateCV as e:
                log_ingest_now(self.conn, "cv", None, "duplicate",
                               detail={"source": src, "existing_cv_id": e.existing_cv_id})
                outcomes[i] = IngestOutcome(src, "duplicate", cv_id=e.existing_cv_id)
                continue
            dedup.add(rec)
            ready.append((i, rec, t0))

        if ready:
            try:
                with_retry(lambda: embed_records([r for _, r, _ in ready], self.encoder),
                           attempts=MAX_ATTEMPTS)
            except Exception as e:  # noqa: BLE001 - GPU het bo nho, model loi...
                ready = self._embed_one_by_one(ready, outcomes, items, e)

        if ready and self._write_batch(ready, outcomes, items):
            return outcomes  # type: ignore[return-value]
        for i, rec, t0 in ready:  # lo loi -> ghi tung CV, CV loi khong chan CV khac
            outcomes[i] = self._write(items[i][0], rec, t0)
        return outcomes  # type: ignore[return-value]

    def _write_batch(self, ready, outcomes, items) -> bool:
        recs = [r for _, r, _ in ready]
        now = time.perf_counter()
        try:
            with_retry(lambda: write_cvs(self.conn, recs,
                                         durations=[int((now - t0) * 1000) for _, _, t0 in ready]),
                       attempts=MAX_ATTEMPTS)
        except Exception as e:  # noqa: BLE001
            log.warning("ghi ca lo loi (%s: %s), ghi lai tung CV", type(e).__name__, e)
            return False
        for i, rec, _ in ready:
            events.emit("cv_committed", events.CvCommitted(rec.cv_id, rec.replaces_cv_id))
            outcomes[i] = IngestOutcome(items[i][0], "ok", cv_id=rec.cv_id, version=rec.version,
                                        flags=list(rec.flags))
        return True

    def _embed_one_by_one(self, ready, outcomes, items, batch_err):
        log.warning("embedding ca lo loi (%s), thu tung CV", batch_err)
        ok = []
        for i, rec, t0 in ready:
            err = None
            for _ in range(MAX_ATTEMPTS):
                try:
                    embed_records([rec], self.encoder)
                    err = None
                    break
                except Exception as e:  # noqa: BLE001
                    err = e
            if err is None:
                ok.append((i, rec, t0))
            else:
                outcomes[i] = self._fail(items[i][0], rec, "A10", err)
        return ok

    def _write(self, src: str, rec: CvRecord, t0: float) -> IngestOutcome:
        last: Exception | None = None
        for _ in range(MAX_ATTEMPTS):
            try:
                write_cv(self.conn, rec, duration_ms=int((time.perf_counter() - t0) * 1000))
                events.emit("cv_committed", events.CvCommitted(rec.cv_id, rec.replaces_cv_id))
                return IngestOutcome(src, "ok", cv_id=rec.cv_id, version=rec.version, flags=list(rec.flags))
            except psycopg.errors.UniqueViolation as e:
                last = e
                break  # khong tu het: vd trung (candidate_key, version) do nap song song
            except Exception as e:  # noqa: BLE001
                last = e
        return self._fail(src, rec, "A11", last)

    def _fail(self, src: str, rec: CvRecord, step: str, err: Exception | None) -> IngestOutcome:
        detail = {"source": src, "step": step, "error": f"{type(err).__name__}: {err}"}
        log_ingest_now(self.conn, "cv", rec.cv_id, "failed", version=rec.version, flags=rec.flags,
                       errors=[detail["error"]], detail=detail)
        return IngestOutcome(src, "failed", cv_id=None, detail=detail)


def delete_cv(conn: psycopg.Connection, cv_id: str) -> bool:
    """Xoa theo yeu cau (thiet ke 03 "Quyen rieng tu"): status = deleted; xoa JSON goc, ban an danh,
    doc_text, vector, token, gach dau dong, evidence_snippet. Phat `cv_deleted` (kem text_raw cac gach)
    de T10 xoa cache BERTScore va T08 go khoi RAM."""
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM cv WHERE cv_id = %s FOR UPDATE", (cv_id,))
            row = cur.fetchone()
            if row is None:
                return False
            cur.execute("SELECT text_raw FROM cv_bullet WHERE cv_id = %s", (cv_id,))
            texts = tuple(r["text_raw"] for r in cur.fetchall())
            cur.execute("UPDATE cv SET status = 'deleted', is_latest = false, raw_json = NULL, anon_json = NULL,"
                        " doc_text = NULL, updated_at = now() WHERE cv_id = %s", (cv_id,))
            cur.execute("DELETE FROM cv_bullet WHERE cv_id = %s", (cv_id,))      # cascade cv_bullet_vector
            cur.execute("DELETE FROM cv_vector WHERE cv_id = %s", (cv_id,))
            cur.execute("DELETE FROM cv_bm25_doc WHERE cv_id = %s", (cv_id,))
            cur.execute("UPDATE cv_skill SET evidence_snippet = NULL WHERE cv_id = %s", (cv_id,))
            cur.execute("UPDATE cv_experience SET title_raw = NULL WHERE cv_id = %s", (cv_id,))
            cur.execute("UPDATE cv_education SET major_raw = NULL WHERE cv_id = %s", (cv_id,))
            log_ingest(cur, "cv", cv_id, "deleted")
    events.emit("cv_deleted", events.CvDeleted(cv_id, texts))
    return True
