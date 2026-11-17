"""Ket noi PostgreSQL + pgvector (thiet ke 03: mot CSDL duy nhat, Postgres la nguon su that).

Dung psycopg 3. Moi buoc ghi cua Luong A/B goi `transaction()` de "hoac du het, hoac khong co gi".
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

DEFAULT_DB_URL = "postgresql://cvmatch:cvmatch@127.0.0.1:5433/cvmatch"
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def db_url() -> str:
    return os.environ.get("CVMATCH_DB_URL", DEFAULT_DB_URL)


def _register_vector(conn: psycopg.Connection) -> None:
    """Dang ky kieu vector/halfvec cua pgvector neu extension da co (sau migration 001)."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        has_ext = cur.fetchone() is not None
    if has_ext:
        from pgvector.psycopg import register_vector

        register_vector(conn)


def connect(url: str | None = None, *, autocommit: bool = True) -> psycopg.Connection:
    """Mac dinh autocommit=True: moi `conn.transaction()` la mot giao dich THAT va commit ngay khi ra
    khoi khoi. (Khong autocommit thi mot SELECT truoc do da ngam mo giao dich, va `transaction()` chi
    con la SAVEPOINT - du lieu chua commit, su kien "sau commit" phat qua som.)"""
    conn = psycopg.connect(url or db_url(), autocommit=autocommit, row_factory=dict_row)
    _register_vector(conn)
    return conn


@contextmanager
def transaction(conn: psycopg.Connection) -> Iterator[psycopg.Cursor]:
    """Mot giao dich: loi bat ky -> rollback toan bo (thiet ke A11, B8)."""
    with conn.transaction():
        with conn.cursor() as cur:
            yield cur


def executemany(cur: psycopg.Cursor, sql: str, rows: Sequence[Sequence[Any] | dict]) -> None:
    if rows:
        cur.executemany(sql, rows)


# --------------------------------------------------------------------------- migrations


def _migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    return sorted(p for p in directory.glob("*.sql") if p.name[:3].isdigit())


def applied_migrations(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        cur.execute("SELECT name FROM schema_migrations")
        return {r["name"] for r in cur.fetchall()}


def migrate(url: str | None = None, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Chay cac file migrations/NNN_*.sql chua chay, theo thu tu; moi file mot giao dich.

    Tra ve danh sach file vua chay. Chay lai lan hai khong lam gi.
    """
    ran: list[str] = []
    with psycopg.connect(url or db_url(), autocommit=True, row_factory=dict_row) as conn:
        done = applied_migrations(conn)
        for path in _migration_files(directory):
            if path.name in done:
                continue
            sql = path.read_text(encoding="utf-8")
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute("INSERT INTO schema_migrations(name) VALUES (%s)", (path.name,))
            ran.append(path.name)
    return ran


def list_tables(conn: psycopg.Connection, schema: str = "public") -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
            (schema,),
        )
        return [r["table_name"] for r in cur.fetchall()]


# --------------------------------------------------------------------------- ghi nhieu dong


def insert_rows(cur: psycopg.Cursor, table: str, cols: tuple[str, ...] | list[str], rows: list[tuple],
                *, chunk: int = 500, suffix: str = "") -> None:
    """Chen nhieu dong bang MOT lenh `INSERT ... VALUES (...), (...)` moi `chunk` dong.

    Khong dung `cursor.executemany`: o psycopg 3 no chay pipeline mode va tren Windows/Docker Desktop
    moi lan goi bi tre ~40 ms (do duoc 187 ms/CV khi ghi, so voi vai ms khi gop lenh).
    """
    if not rows:
        return
    ph = "(" + ", ".join(["%s"] * len(cols)) + ")"
    head = f"INSERT INTO {table}({', '.join(cols)}) VALUES "
    for s in range(0, len(rows), chunk):
        part = rows[s:s + chunk]
        cur.execute(head + ", ".join([ph] * len(part)) + (f" {suffix}" if suffix else ""),
                    [x for r in part for x in r])
