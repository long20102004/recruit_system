"""Tinh san token embedding BERTScore (S05, V-12).

Rerank lan dau voi mot CV / JD phai tinh token embedding cho tung gach (CPU ~250 ms / CV, do o
`research/reports/bench_cpu.md`), lan sau doc cache (~6 ms / CV). Tinh san o hai cho:

- ngay sau khi nap CV / JD (`Services.ingest_*`), de lan match dau khong cham;
- luc khoi dong, chay nen: JD dang mo + CV trong chi muc ma cache (DB) chua co, co gioi han thoi gian.

Cache luu o bang `bertscore_token_cache` (theo `bertscore_config`), nen da tinh mot lan la dung lai sau khi khoi
dong lai.
"""

from __future__ import annotations

import time

import psycopg


def cv_texts(conn: psycopg.Connection, cv_ids: list[str]) -> list[str]:
    if not cv_ids:
        return []
    return [r["text_raw"] for r in conn.execute(
        "SELECT text_raw FROM cv_bullet WHERE cv_id = ANY(%s::uuid[]) UNION ALL"
        " SELECT text_raw FROM cv_summary_sentence WHERE cv_id = ANY(%s::uuid[])", (cv_ids, cv_ids))]


def jd_texts(conn: psycopg.Connection, jd_keys: list[tuple[str, int]] | None = None) -> list[str]:
    """`jd_keys` None -> moi JD dang mo, ban moi nhat."""
    if jd_keys is None:
        where, args = "j.is_latest AND j.status = 'open'", ()
    elif not jd_keys:
        return []
    else:
        where = "(j.jd_id, j.version) IN (SELECT * FROM unnest(%s::text[], %s::int[]))"
        args = ([k for k, _ in jd_keys], [v for _, v in jd_keys])
    sql = (f"SELECT r.text_raw FROM jd_responsibility r JOIN jd j USING (jd_id, version) WHERE {where} UNION ALL"
           f" SELECT q.text_raw FROM jd_requirement_item q JOIN jd j USING (jd_id, version) WHERE {where}")
    return [r["text_raw"] for r in conn.execute(sql, args + args)]


def precompute(scorer, texts: list[str], *, batch: int = 64, deadline: float | None = None) -> int:
    """Tinh token embedding cho `texts` (bo qua cai da co). Tra ve so van ban da xu ly."""
    texts = list(dict.fromkeys(t for t in texts if t))
    done = 0
    for s in range(0, len(texts), batch):
        if deadline is not None and time.monotonic() > deadline:
            break
        chunk = texts[s:s + batch]
        scorer.embed(scorer.prepare(chunk))
        done += len(chunk)
    return done
