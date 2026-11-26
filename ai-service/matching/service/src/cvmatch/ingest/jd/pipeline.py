"""Luong B: JD JSON -> JdRecord (B1-B7, thuan tru phan embedding) va dich vu nap (B8)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import psycopg

from cvmatch.core.models import Encoder
from cvmatch.core import events
from cvmatch.ingest.common.writer import log_ingest_now, with_retry
from cvmatch.ingest.jd.prepare import step_b01, step_b02, step_b03
from cvmatch.ingest.jd.skills import step_b04
from cvmatch.ingest.jd.requirements import step_b05
from cvmatch.ingest.jd.bm25_tokens import step_b07_tokens
from cvmatch.ingest.jd.embed import embed_jd_records
from cvmatch.ingest.jd.responsibilities import step_b06
from cvmatch.ingest.jd.write import compute_warnings, write_jd
from cvmatch.ingest.jd.record import JdRecord, PrepContext, UnchangedJD
from cvmatch.ingest.jd.schema import InvalidJD


def build_jd_record(raw: Any, ctx: PrepContext, versions=None) -> JdRecord:
    """B1-B7 (tru vector) + canh bao B8. Dung som: InvalidJD, UnchangedJD."""
    rec = step_b01(raw, ctx, versions)
    for step in (step_b02, step_b03, step_b04, step_b05, step_b06, step_b07_tokens):
        rec = step(rec, ctx)
    rec.warnings = compute_warnings(rec, ctx)
    return rec


class PgJdVersions:
    """`latest` -> (version lon nhat, raw_json cua no neu CUNG bo khoa phien ban, khong thi None): JD giong het
    nhung o bo khoa khac (vd sau khi doi KB) khong bi coi la `unchanged` - phai nap ban moi."""

    def __init__(self, conn: psycopg.Connection, keys: tuple[str, str, str] | None = None):
        self.conn = conn
        self.keys = keys

    def latest(self, jd_id: str) -> tuple[int, dict | None] | None:
        row = self.conn.execute("SELECT version, raw_json, ontology_version, pipeline_version, embed_model FROM jd"
                                " WHERE jd_id = %s ORDER BY version DESC LIMIT 1", (jd_id,)).fetchone()
        if row is None:
            return None
        same = self.keys is None or (row["ontology_version"], row["pipeline_version"], row["embed_model"]) == self.keys
        return int(row["version"]), (row["raw_json"] if same else None)


@dataclass
class JdOutcome:
    source: str
    status: str                 # ok | invalid | unchanged | failed
    jd_id: str | None = None
    version: int | None = None
    warnings: list[dict] = field(default_factory=list)
    detail: dict = field(default_factory=dict)


class JdIngestor:
    def __init__(self, conn: psycopg.Connection, ctx: PrepContext, encoder: Encoder):
        self.conn, self.ctx, self.encoder = conn, ctx, encoder

    def ingest_one(self, raw: Any, source: str = "api") -> JdOutcome:
        t0 = time.perf_counter()
        try:
            rec = build_jd_record(raw, self.ctx, PgJdVersions(
                self.conn, (self.ctx.snapshot.ontology_version, self.ctx.cfg.prep.version, self.encoder.key())))
        except InvalidJD as e:
            log_ingest_now(self.conn, "jd", e.jd_id, "invalid", errors=e.errors, detail={"source": source})
            return JdOutcome(source, "invalid", jd_id=e.jd_id, detail={"errors": e.errors})
        except UnchangedJD as e:
            return JdOutcome(source, "unchanged", jd_id=e.jd_id, version=e.version)
        try:
            with_retry(lambda: embed_jd_records([rec], self.encoder))
            with_retry(lambda: write_jd(self.conn, rec, duration_ms=int((time.perf_counter() - t0) * 1000)))
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            log_ingest_now(self.conn, "jd", rec.jd_id, "failed", version=rec.version, errors=[err],
                           detail={"source": source})
            return JdOutcome(source, "failed", jd_id=rec.jd_id, detail={"error": err})
        events.emit("jd_committed", events.JdCommitted(rec.jd_id, rec.version))
        return JdOutcome(source, "ok", jd_id=rec.jd_id, version=rec.version, warnings=rec.warnings)

    def ingest_many(self, items: list[tuple[str, Any]]) -> list[JdOutcome]:
        return [self.ingest_one(raw, src) for src, raw in items]


def set_jd_status(conn: psycopg.Connection, jd_id: str, status: str) -> int | None:
    """JD mo / dong / het han: chi cap nhat `status` cua phien ban moi nhat, khong tinh lai vector."""
    if status not in ("open", "draft", "closed", "expired"):
        raise ValueError(f"status khong hop le: {status}")
    with conn.transaction():
        # trang thai la cua TIN TUYEN DUNG: ap cho moi ban (ke ca ban song song cua phien ban khac)
        row = conn.execute("UPDATE jd SET status = %s, updated_at = now() WHERE jd_id = %s AND is_latest"
                           " RETURNING version", (status, jd_id)).fetchone()
        if row is not None:
            conn.execute("UPDATE jd SET status = %s, updated_at = now() WHERE jd_id = %s AND NOT is_latest",
                         (status, jd_id))
    if row is None:
        return None
    events.emit("jd_status_changed", events.JdStatusChanged(jd_id, row["version"], status))
    return row["version"]
