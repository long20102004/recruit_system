"""Tien ich ghi dung chung cho Luong A (A11) va B (B8)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from typing import TypeVar

import numpy as np
import psycopg
from pgvector import HalfVector
from psycopg.types.json import Jsonb

from cvmatch.core.db import insert_rows  # noqa: F401 - dung chung, dinh nghia o core

log = logging.getLogger(__name__)
T = TypeVar("T")

# Loi tam thoi -> thu lai (thiet ke 03: "thu lai tu dong toi da 3 lan")
TRANSIENT = (psycopg.OperationalError, psycopg.errors.SerializationFailure,
             psycopg.errors.DeadlockDetected)


def with_retry(fn: Callable[[], T], attempts: int = 3, base_delay: float = 0.2) -> T:
    for i in range(attempts):
        try:
            return fn()
        except TRANSIENT as e:
            if i == attempts - 1:
                raise
            log.warning("loi tam thoi (%s), thu lai lan %d", type(e).__name__, i + 2)
            time.sleep(base_delay * (2 ** i))
    raise AssertionError("unreachable")


def halfvec(x: np.ndarray) -> HalfVector:
    return HalfVector(np.asarray(x, dtype=np.float32))


def jsonb(x) -> Jsonb:
    return Jsonb(x)


def log_ingest(cur: psycopg.Cursor, entity: str, entity_id: str | None, status: str, *,
               version: int | None = None, errors: list | None = None, flags: Iterable[str] = (),
               detail: dict | None = None, duration_ms: int | None = None) -> None:
    cur.execute(
        "INSERT INTO ingest_log(entity, entity_id, version, status, errors, flags, detail, duration_ms)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (entity, entity_id, version, status, jsonb(errors or []), list(flags), jsonb(detail or {}),
         duration_ms),
    )


def log_ingest_now(conn: psycopg.Connection, *args, **kwargs) -> None:
    """Ghi ingest_log trong giao dich RIENG (CV dung som o A1/A2, hoac loi sau khi rollback)."""
    with conn.transaction():
        with conn.cursor() as cur:
            log_ingest(cur, *args, **kwargs)


def upsert_unknown_skills(cur: psycopg.Cursor, items: Iterable[tuple], source: str) -> None:
    """Cum chua co trong KB: da co thi count + n, chua co thi them dong (A5, B4).

    `items`: (text, example) hoac (text, example, n) - text phai khac nhau (da gop o caller).
    """
    rows = [(it[0], it[2] if len(it) > 2 else 1, it[1], [source]) for it in items]
    if rows:
        insert_rows(cur, "unknown_skill", ("text", "count", "example", "sources"), rows,
                    suffix="ON CONFLICT (text) DO UPDATE SET count = unknown_skill.count + EXCLUDED.count,"
                           " last_seen = now(),"
                           " sources = ARRAY(SELECT DISTINCT unnest(unknown_skill.sources || EXCLUDED.sources))")
