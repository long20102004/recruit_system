"""`cvmatch run-e2e`: chay TRON JD tu JSON den giai thich (moc P1, thiet ke 11 muc 2).

migrate (neu can) -> nap KB snapshot (neu chua co) -> nap CV, JD -> Retrieve -> Rerank -> Explain top 5.
Cung lan chay xuat top 30 theo `fused` cua Retrieve (R-A0, khong rerank) de so tay.
Ket qua: `<out>/<ts>/summary.json`, `report.md`, log JSON `run.jsonl` (`run_id` xuyen suot).
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

from cvmatch.api.logjson import Timer, detach_file, log_event, setup_json_logging
from cvmatch.api.services import Services, config_and_encoder
from cvmatch.core.db import connect, db_url, migrate
from cvmatch.core.kb.store import import_snapshot, list_versions, read_snapshot_dir


def create_database(base_url: str, name: str) -> str:
    """Tao database moi tren cung server (giu lai sau khi chay de xem). -> url cua no."""
    import psycopg
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    with psycopg.connect(base_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    params = conninfo_to_dict(base_url)
    params["dbname"] = name
    return make_conninfo(**params)


def _json_files(path: Path) -> list[tuple[str, object]]:
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    return [(str(f), json.loads(f.read_text(encoding="utf-8"))) for f in files]


def _memory() -> dict:
    out: dict = {}
    try:
        import psutil

        out["rss_mb"] = round(psutil.Process().memory_info().rss / 2**20, 1)
    except ImportError:
        pass
    try:
        import sys

        torch = sys.modules.get("torch")
        if torch is not None and torch.cuda.is_available():
            out["gpu_max_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
    except Exception:  # noqa: BLE001
        pass
    return out


def run_e2e(cv_dir: str | Path, jd_path: str | Path, *, url: str | None = None, config_dir=None,
            kb_dir: str | Path | None = None, fake: bool = False, out_dir: str | Path = "reports/e2e",
            n_explain: int = 5, n_retrieve_top: int = 30, ref_ym: str | None = None, hmac_key: str | None = None,
            N: int | None = None, K: int | None = None) -> dict:
    url = url or db_url()
    run_dir = Path(out_dir) / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = (run_dir / "run.jsonl").resolve()
    setup_json_logging(log_path)
    timings: dict[str, float] = {}
    try:
        with Timer() as t:                                                        # 1. migrate
            ran = migrate(url)
        timings["migrate_s"] = t.s
        log_event("e2e_migrate", ran=ran, duration_s=t.s)

        overrides: dict = {}
        if kb_dir is not None:                                                    # 2. KB snapshot
            version = read_snapshot_dir(kb_dir)[0]["ontology_version"]
            with connect(url) as conn, Timer() as t:
                have = {r["ontology_version"] for r in list_versions(conn)}
                if version not in have:
                    import_snapshot(conn, kb_dir)
            timings["kb_import_s"] = t.s
            log_event("e2e_kb", ontology_version=version, imported=version not in have, duration_s=t.s)
            overrides["ontology_version"] = version
        cfg, enc = config_and_encoder(config_dir, fake=fake, overrides=overrides)

        key = hmac_key or os.environ.get("CVMATCH_HMAC_KEY") or "e2e-local-key"
        with Services(cfg, url=url, encoder=enc, hmac_key=key) as svc:
            timings.update({f"services.{k}": v for k, v in svc.timings.items()})
            cv_items = _json_files(Path(cv_dir))                                  # 3. nap CV, JD
            with Timer() as t:
                cv_out = svc.ingest_cvs(cv_items)
            timings["ingest_cv_s"] = t.s
            jd_items = _json_files(Path(jd_path))
            with Timer() as t:
                jd_out = [svc.ingest_jd(raw, src) for src, raw in jd_items]
            timings["ingest_jd_s"] = t.s
            cv_status = dict(Counter(o.status for o in cv_out))
            bad = [{"source": o.source, "status": o.status, "detail": o.detail} for o in cv_out
                   if o.status not in ("ok", "duplicate")]

            runs = []
            for o in jd_out:                                                      # 4-6. match + explain
                if o.status not in ("ok", "unchanged"):
                    runs.append({"jd_id": o.jd_id, "status": o.status, "detail": o.detail})
                    continue
                m = svc.match_jd(o.jd_id, K=K, N=N, ref_ym=ref_ym, n_retrieve_top=n_retrieve_top)
                with Timer() as t:
                    expl = [svc.explain(m.run_id, it["cv_id"]) for it in m.items[:n_explain]]
                m.timings["explain_top_s"] = t.s
                rr_rank = {it["cv_id"]: it for it in m.items}
                runs.append({
                    "jd_id": m.jd_id, "jd_version": m.jd_version, "status": "ok", "jd_warnings": o.warnings,
                    "run_id": m.run_id, "retrieve_run_id": m.retrieve_run_id, "n_pool": m.n_pool,
                    "warnings": m.warnings, "timings": m.timings,
                    "rerank_top": m.items,
                    "retrieve_top": [{**r, "rerank_rank": (rr_rank.get(r["cv_id"]) or {}).get("rank"),
                                      "rerank_score": (rr_rank.get(r["cv_id"]) or {}).get("score")}
                                     for r in m.retrieve_top],
                    "explanations": [{"cv_id": e["cv_id"], "score": e["score"], "band": e["band"], "text": e["text"]}
                                     for e in expl],
                })
            mem = {**_memory(), "index_mb": svc.index.memory_mb()}
            versions = svc.cfg.versions.model_dump()
            sources = {o.cv_id: Path(o.source).name for o in cv_out if o.cv_id}   # duplicate: cv_id ban da co
        summary = {"url_db": _mask(url), "versions": versions, "fake_encoder": fake, "timings": timings,
                   "memory": mem, "cv_status": cv_status, "cv_problems": bad,
                   "jd_status": [{"source": o.source, "jd_id": o.jd_id, "status": o.status, "version": o.version}
                                 for o in jd_out], "cv_sources": sources, "runs": runs, "log": str(log_path), "dir": str(run_dir)}
        (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str),
                                              encoding="utf-8")
        (run_dir / "report.md").write_text(to_markdown(summary, sources), encoding="utf-8")
        log_event("e2e_done", dir=str(run_dir), **timings)
        return summary
    finally:
        detach_file(log_path)


def _mask(url: str) -> str:
    import re

    return re.sub(r"//([^:/@]+):[^@]*@", r"//\1:***@", url)


def to_markdown(s: dict, sources: dict) -> str:
    name = lambda cv_id: sources.get(cv_id, cv_id[:8])  # noqa: E731
    v = s["versions"]
    out = ["# Chạy trọn JD → giải thích (run-e2e)", "",
           f"- Phiên bản: `{v['ontology_version']}` · `{v['pipeline_version']}` · `{v['embed_model']}` · "
           f"`{v['bertscore_config']}` · `{v['rerank_config_version']}`" + (" · **FakeEncoder**" if s["fake_encoder"] else ""),
           f"- CV: {s['cv_status']} · JD: " + ", ".join(f"{j['jd_id']} {j['status']}" for j in s["jd_status"]),
           f"- Thời gian (s): " + ", ".join(f"{k} {val}" for k, val in s["timings"].items()),
           f"- Bộ nhớ: {s['memory']}", f"- Log: `{s['log']}`"]
    for r in s["runs"]:
        if r["status"] != "ok":
            out += ["", f"## {r['jd_id']}: {r['status']}", "", f"```\n{r.get('detail')}\n```"]
            continue
        t = r["timings"]
        out += ["", f"## {r['jd_id']} v{r['jd_version']}", "",
                f"rerank run `{r['run_id']}` · retrieve run `{r['retrieve_run_id']}` · pool {r['n_pool']} CV · "
                f"retrieve {t.get('retrieve_s')}s · rerank {t.get('rerank_s')}s "
                f"(BERTScore {t.get('rerank.rr2_bertscore_s', 0)}s) · explain top {len(r['explanations'])} "
                f"{t.get('explain_top_s')}s"]
        for w in r["warnings"] + r["jd_warnings"]:
            out.append(f"- cảnh báo: {w.get('message') or w}")
        out += ["", "### Top sau Rerank", "", "| Hạng | Điểm | Dải | Trần | CV | Cờ |", "| --- | --- | --- | --- | --- | --- |"]
        out += [f"| {it['rank']} | {it['score']} | {it['band']} | {'có' if it['cap_applied'] else ''} | {name(it['cv_id'])}"
                f" | {', '.join(it['flags'])} |" for it in r["rerank_top"]]
        out += ["", "### R-A0: top theo `fused` của Retrieve (không rerank)", "",
                "| Hạng fused | fused | dense | bm25 | skill | resp | CV | Hạng rerank | Điểm |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        f3 = lambda x: "–" if x is None else f"{x:.3f}"  # noqa: E731
        out += [f"| {x['rank']} | {x['fused']:.3f} | {f3(x['s']['dense'])} | {f3(x['s']['bm25'])} | {f3(x['s']['skill'])}"
                f" | {f3(x['s']['resp'])} | {name(x['cv_id'])} | {x['rerank_rank'] or '–'} | {x['rerank_score'] if x['rerank_score'] is not None else '–'} |"
                for x in r["retrieve_top"]]
        out += ["", f"### Giải thích top {len(r['explanations'])}", ""]
        for e in r["explanations"]:
            out += [f"#### {name(e['cv_id'])} · {e['score']} ({e['band']})", "", e["text"], ""]
    return "\n".join(out) + "\n"
