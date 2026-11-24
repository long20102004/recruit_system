from __future__ import annotations

import os
import uuid

import pytest


def _db_reachable(url: str) -> bool:
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=3):
            return True
    except Exception:
        return False


@pytest.fixture()
def fresh_db_url():
    """Tao mot database rieng cho test tren Postgres o CVMATCH_DB_URL, xoa sau khi xong.

    Khong co Postgres -> skip (test danh dau @pytest.mark.db).
    """
    import psycopg
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    from cvmatch.core.db import db_url

    base = db_url()
    if not _db_reachable(base):
        pytest.skip(f"khong ket noi duoc Postgres ({base}); chay `docker compose up -d`")
    name = f"cvmatch_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    params = conninfo_to_dict(base)
    params["dbname"] = name
    url = make_conninfo(**params)
    try:
        yield url
    finally:
        with psycopg.connect(base, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture(autouse=True)
def _no_env_leak(monkeypatch):
    # Test config luon dung thu muc config mac dinh, khong bi bien moi truong cua may lam lech
    monkeypatch.delenv("CVMATCH_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CVMATCH_DEVICE", raising=False)
    yield
    os.environ.pop("CVMATCH_FAKE_ENCODER", None)


# --------------------------------------------------------------------------- KB mini (dung chung moi nhom test)

from pathlib import Path as _Path

FIXTURES = _Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def kb_mini():
    from cvmatch.core.kb.snapshot import KBSnapshot

    return KBSnapshot.from_dir(FIXTURES / "kb_mini")


@pytest.fixture(scope="session")
def matcher(kb_mini):
    from cvmatch.core.kb.matcher import SkillMatcher

    return SkillMatcher(kb_mini)


@pytest.fixture(scope="session")
def lookup(kb_mini):
    from cvmatch.core.kb.lookup import TitleLookup

    return TitleLookup(kb_mini)
