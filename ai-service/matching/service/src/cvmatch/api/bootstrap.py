"""Chuan bi truoc khi chay API trong container (I01): cho Postgres -> migrate -> nap KB snapshot neu chua co.

Moi buoc idempotent: khoi dong lai container khong lam gi them khi DB da san sang.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from cvmatch.api.logjson import log_event
from cvmatch.core.config import AppConfig
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.store import import_snapshot, list_versions

WEAK_HMAC_KEYS = {"", "change-me", "changeme"}


class BootstrapError(RuntimeError):
    pass


def check_secrets(env: str | None = None) -> None:
    """prod: khoa HMAC that (doi khoa = moi candidate_key doi -> phai nap lai toan bo CV)."""
    env = env or os.environ.get("CVMATCH_ENV", "dev")
    key = os.environ.get("CVMATCH_HMAC_KEY", "")
    if env == "prod" and key.strip().lower() in WEAK_HMAC_KEYS:
        raise BootstrapError("CVMATCH_ENV=prod can CVMATCH_HMAC_KEY that (khong de trong / change-me)")
    if not key:
        raise BootstrapError("thieu CVMATCH_HMAC_KEY")


def wait_for_db(url: str, *, timeout_s: float = 120.0, interval_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with connect(url) as conn:
                conn.execute("SELECT 1").fetchone()
            return
        except Exception as e:  # noqa: BLE001 - Postgres chua len thi thu lai
            last = e
            time.sleep(interval_s)
    raise BootstrapError(f"khong ket noi duoc Postgres sau {timeout_s:.0f}s: {last}")


def ensure_kb(url: str, cfg: AppConfig, kb_dir: str | Path | None) -> str:
    """Ban `cfg.ontology_version` chua co trong DB -> nap tu `kb_dir/<version>`. Tra ve version dang dung."""
    version = cfg.ontology_version
    with connect(url) as conn:
        have = {r["ontology_version"] for r in list_versions(conn)}
        if version is None:
            if not have:
                raise BootstrapError("chua chon ontology_version (active.yaml / CVMATCH_ONTOLOGY_VERSION) va DB chua co KB")
            return sorted(have)[-1]
        if version in have:
            return version
        if not kb_dir:
            raise BootstrapError(f"KB {version} chua nap va khong co CVMATCH_KB_DIR")
        path = Path(kb_dir) / version
        if not (path / "manifest.json").exists():
            raise BootstrapError(f"khong thay snapshot {path} (mount ai-service/matching/kb-builder/out/snapshot vao CVMATCH_KB_DIR)")
        got = import_snapshot(conn, path)
    log_event("kb_imported", ontology_version=got, path=str(path))
    return got


def bootstrap(url: str, cfg: AppConfig, *, kb_dir: str | Path | None = None, db_timeout_s: float = 120.0) -> dict:
    check_secrets()
    wait_for_db(url, timeout_s=db_timeout_s)
    ran = migrate(url)
    version = ensure_kb(url, cfg, kb_dir)
    log_event("bootstrap_done", migrations=ran, ontology_version=version)
    return {"migrations": ran, "ontology_version": version}
