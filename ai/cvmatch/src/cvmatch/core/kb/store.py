"""Nap ban chup KB (thu muc do build_kb/export_snapshot.py xuat) vao Postgres, va doc lai (T01).

- `import_snapshot`: kiem sha256 tung file theo manifest, nap 5 bang + `kb_version` trong MOT giao
  dich. Version da co -> tu choi (tru `replace=True` voi ban `-dev`).
- `load_snapshot_db`: doc lai thanh `KBSnapshot` (cung dang voi `KBSnapshot.from_dir`).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import psycopg

from cvmatch.core.kb.snapshot import SNAPSHOT_FILES, KBSnapshot

_COLS = {
    "skill_ontology": ("skill_id", "name", "aliases", "type", "parents", "categories_sibling_ok", "status"),
    "role_title_map": ("kind", "alias", "role_group", "level_rank"),
    "role_distance": ("group_a", "group_b", "m", "method"),
    "major_group": ("major_alias", "group"),
    "ambiguous_aliases": ("alias", "candidates"),
}


# Truong thieu trong JSONL -> gia tri mac dinh (cot NOT NULL)
_DEFAULTS = {"aliases": [], "parents": [], "categories_sibling_ok": [], "candidates": [], "status": "accepted"}


class SnapshotError(Exception):
    pass


def read_snapshot_dir(path: str | Path) -> tuple[dict, dict[str, list[dict]]]:
    p = Path(path)
    manifest = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = {}
    for name in SNAPSHOT_FILES:
        text = (p / f"{name}.jsonl").read_text(encoding="utf-8")
        expected = (manifest.get("files") or {}).get(name, {}).get("sha256")
        if expected and hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
            raise SnapshotError(f"{name}.jsonl khong khop sha256 trong manifest (file bi sua?)")
        rows[name] = [json.loads(line) for line in text.splitlines() if line.strip()]
    return manifest, rows


def import_snapshot(conn: psycopg.Connection, path: str | Path, *, replace: bool = False) -> str:
    manifest, rows = read_snapshot_dir(path)
    version = manifest["ontology_version"]
    KBSnapshot.from_rows(manifest, rows)  # kiem alias trung theo dung ham chuan hoa A4 truoc khi ghi
    with conn.transaction():
        exists = conn.execute("SELECT 1 FROM kb_version WHERE ontology_version = %s", (version,)).fetchone()
        if exists:
            if not (replace and version.endswith("-dev")):
                raise SnapshotError(f"{version} da duoc nap; chi ban -dev moi duoc --replace")
            conn.execute("DELETE FROM kb_version WHERE ontology_version = %s", (version,))  # cascade 5 bang
        conn.execute(
            "INSERT INTO kb_version(ontology_version, created_at, include_candidate, manifest)"
            " VALUES (%s, %s, %s, %s)",
            (version, manifest.get("created_at"), bool(manifest.get("include_candidate")),
             json.dumps(manifest, ensure_ascii=False)))
        with conn.cursor() as cur:
            for name, cols in _COLS.items():
                data = [(version, *(r.get(c, _DEFAULTS.get(c)) if r.get(c) is not None else _DEFAULTS.get(c)
                                    for c in cols)) for r in rows[name]]
                if not data:
                    continue
                qcols = ", ".join(f'"{c}"' for c in cols)
                ph = "(" + ", ".join(["%s"] * (len(cols) + 1)) + ")"
                for s in range(0, len(data), 1000):
                    part = data[s:s + 1000]
                    cur.execute(f"INSERT INTO {name}(ontology_version, {qcols}) VALUES "
                                + ", ".join([ph] * len(part)), [x for r in part for x in r])
    return version


def list_versions(conn: psycopg.Connection) -> list[dict]:
    return conn.execute("SELECT ontology_version, created_at, imported_at, include_candidate FROM kb_version"
                        " ORDER BY imported_at DESC").fetchall()


def load_snapshot_db(conn: psycopg.Connection, version: str | None = None) -> KBSnapshot:
    """version None -> ban nap gan nhat."""
    if version is None:
        row = conn.execute("SELECT ontology_version FROM kb_version ORDER BY imported_at DESC LIMIT 1").fetchone()
        if row is None:
            raise SnapshotError("chua nap ban chup KB nao (cvmatch kb import)")
        version = row["ontology_version"]
    mrow = conn.execute("SELECT manifest FROM kb_version WHERE ontology_version = %s", (version,)).fetchone()
    if mrow is None:
        raise SnapshotError(f"khong co ban chup {version}")
    rows = {}
    for name, cols in _COLS.items():
        qcols = ", ".join(f'"{c}"' for c in cols)
        rows[name] = [dict(r) for r in conn.execute(
            f"SELECT {qcols} FROM {name} WHERE ontology_version = %s", (version,)).fetchall()]
    return KBSnapshot.from_rows(mrow["manifest"], rows)
