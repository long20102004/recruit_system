"""DedupLookup tren Postgres cho A2 (bang `cv`, cot `content_hash`, `candidate_key` co index)."""

from __future__ import annotations

import psycopg

from cvmatch.ingest.cv.record import CvRecord, InMemoryDedup


class PgDedup:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def find_by_hash(self, content_hash: str) -> str | None:
        row = self.conn.execute(
            "SELECT cv_id FROM cv WHERE content_hash = %s AND status <> 'deleted' LIMIT 1",
            (content_hash,)).fetchone()
        return str(row["cv_id"]) if row else None

    def latest_version(self, candidate_key: str) -> tuple[str, int] | None:
        row = self.conn.execute(
            "SELECT cv_id, version FROM cv WHERE candidate_key = %s ORDER BY version DESC LIMIT 1",
            (candidate_key,)).fetchone()
        return (str(row["cv_id"]), int(row["version"])) if row else None


class BatchDedup:
    """Postgres + cac CV da dung trong cung lo (chua ghi) - de hai file giong nhau trong mot lo
    cung bi bat trung, va hai ban cua cung nguoi trong mot lo nhan version tang dan."""

    def __init__(self, base: PgDedup):
        self.base = base
        self.pending = InMemoryDedup()

    def find_by_hash(self, content_hash: str) -> str | None:
        return self.pending.find_by_hash(content_hash) or self.base.find_by_hash(content_hash)

    def latest_version(self, candidate_key: str) -> tuple[str, int] | None:
        return self.pending.latest_version(candidate_key) or self.base.latest_version(candidate_key)

    def add(self, rec: CvRecord) -> None:
        self.pending.add(rec)
