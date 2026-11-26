"""Dung moi truong demo "nhu that": DB Postgres rieng (`cvmatch_demo`), KB that, vai tram CV + 30 JD da nap san
qua dung Luong A / B (bge-m3 that tren GPU, hoac FakeEncoder), roi chay API tren DB do.

    cvmatch demo seed     -> sinh du lieu (data/demo/) + tao DB + migrate + nap KB + nap CV, ban CV moi, JD
    cvmatch demo serve    -> chay API tren DB demo (cung KB, cung khoa HMAC, cung encoder)
    cvmatch demo scenarios-> chay bo kich ban HTTP vao API dang chay

`data/demo/state.json` (khong commit) ghi DB, KB, encoder, khoa HMAC cuc bo va anh xa file -> cv_id / jd_id.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from cvmatch.core.db import connect, db_url, migrate

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "demo"
# ai-service/matching = thu muc cha dau tien co kb-builder (trong container khong co -> duong dan tuong doi, chi dung khi chay demo)
_MATCHING = next((p for p in Path(__file__).resolve().parents if (p / "kb-builder").is_dir()), Path("."))
DEFAULT_KB = _MATCHING / "kb-builder" / "out" / "snapshot" / "kb-2026-11-21-4"
DEMO_HMAC = "demo-local-hmac-key"          # chi cho du lieu gia cua moi truong demo


def _with_db(base_url: str, name: str) -> str:
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    p = conninfo_to_dict(base_url)
    p["dbname"] = name
    return make_conninfo(**p)


def ensure_database(base_url: str, name: str, *, reset: bool = False) -> tuple[str, bool]:
    """-> (url, tao_moi)."""
    import psycopg

    with psycopg.connect(base_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone() is not None
        if exists and reset:
            conn.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
            exists = False
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')
    return _with_db(base_url, name), not exists


def load_state(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_DIR / "state.json"
    if not p.exists():
        raise FileNotFoundError(f"chua co {p} - chay `cvmatch demo seed` truoc")
    return json.loads(p.read_text(encoding="utf-8"))


def services_from_state(state: dict):
    from cvmatch.api.services import Services, config_and_encoder

    cfg, enc = config_and_encoder(state.get("config_dir"), fake=state["fake_encoder"],
                                  overrides={"ontology_version": state["kb_version"]})
    return Services(cfg, url=state["db_url"], encoder=enc, hmac_key=state["hmac_key"])


def _files(d: Path) -> list[tuple[str, dict]]:
    return [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(d.glob("*.json"))]


def seed(*, data_dir: str | Path = DEFAULT_DIR, base_url: str | None = None, db_name: str = "cvmatch_demo",
         kb_dir: str | Path = DEFAULT_KB, n_cv: int = 300, fake: bool = False, reset: bool = False,
         regenerate: bool = False, batch: int = 32, data_seed: int = 2026, log=print) -> dict:
    from cvmatch.core.kb.store import import_snapshot, list_versions, read_snapshot_dir
    from cvmatch.demo.generate import generate

    data_dir = Path(data_dir)
    t0 = time.perf_counter()
    if regenerate or not (data_dir / "manifest.json").exists():
        log(f"sinh du lieu: {generate(data_dir, n_cv=n_cv, seed=data_seed)}")
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    url, created = ensure_database(base_url or db_url(), db_name, reset=reset)
    log(f"database {db_name}: {'tao moi' if created else 'da co (nap bo sung, CV trung bi bo qua)'}")
    ran = migrate(url)
    if ran:
        log(f"migrate: {', '.join(ran)}")
    kb_version = read_snapshot_dir(kb_dir)[0]["ontology_version"]
    with connect(url) as conn:
        if kb_version not in {r["ontology_version"] for r in list_versions(conn)}:
            import_snapshot(conn, kb_dir)
            log(f"nap KB {kb_version}")
    state = {"db_name": db_name, "db_url": url, "kb_version": kb_version, "kb_dir": str(kb_dir), "fake_encoder": fake,
             "hmac_key": DEMO_HMAC, "data_dir": str(data_dir), "cv": {}, "cv_updates": {}, "jd": {}, "timings": {}}
    from cvmatch.api.services import Services, config_and_encoder

    cfg, enc = config_and_encoder(fake=fake, overrides={"ontology_version": kb_version})
    with Services(cfg, url=url, encoder=enc, hmac_key=DEMO_HMAC) as svc:
        state["timings"]["load_s"] = round(time.perf_counter() - t0, 1)
        state["versions"] = svc.cfg.versions.model_dump()
        for sub in ("cv", "cv_updates"):
            items = _files(data_dir / sub)
            t = time.perf_counter()
            counts: dict[str, int] = {}
            for s in range(0, len(items), batch):
                outs = svc.ingest_cvs(items[s:s + batch], batch_size=batch)
                for (name, _), o in zip(items[s:s + batch], outs):
                    counts[o.status] = counts.get(o.status, 0) + 1
                    if o.cv_id:
                        state[sub][name] = {"cv_id": o.cv_id, "status": o.status, "version": o.version,
                                            **manifest[sub][name]}
                log(f"  {sub}: {min(s + batch, len(items))}/{len(items)} · {counts}")
            state["timings"][f"ingest_{sub}_s"] = round(time.perf_counter() - t, 1)
        t = time.perf_counter()
        jd_counts: dict[str, int] = {}
        for name, raw in _files(data_dir / "jd"):
            o = svc.ingest_jd(raw, name)
            jd_counts[o.status] = jd_counts.get(o.status, 0) + 1
            state["jd"][raw["jd_id"]] = {"version": o.version, "ingest_status": o.status,
                                         "warnings": [w["code"] for w in o.warnings], **manifest["jd"][raw["jd_id"]]}
        log(f"  jd: {jd_counts}")
        state["timings"]["ingest_jd_s"] = round(time.perf_counter() - t, 1)
        h = svc.health()
        state["n_cv_index"] = h["n_cv"]
        state["n_jd_open"] = h["n_jd_open"]
    state["timings"]["total_s"] = round(time.perf_counter() - t0, 1)
    (data_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"xong: {state['n_cv_index']} CV trong chi muc, {state['n_jd_open']} JD mo · {state['timings']}")
    log(f"state: {data_dir / 'state.json'}")
    return state
