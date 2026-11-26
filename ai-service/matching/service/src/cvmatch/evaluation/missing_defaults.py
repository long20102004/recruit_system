"""S02: do gia tri co dinh cho feature thieu PHIA CV (`missing.cv_side_policy = fixed`).

Lay trung vi tung feature tren cac lan rerank da luu (`rerank_feature`), CHI tinh gia tri that: bo o feature do thieu
(co trong `missing_json`). Moi cap (truy van, ung vien) chi tinh mot lan (lan chay moi nhat) de JD / CV duoc chay nhieu
lan khong lam lech trung vi. Ket qua la YAML de dan vao `missing.cv_side_fixed` cua `rr-1.x.yaml`.
"""

from __future__ import annotations

import psycopg

SQL = """
WITH latest AS (
    SELECT DISTINCT ON (m.query_id, f.item_id) f.features_json, f.missing_json
    FROM rerank_feature f
    JOIN rerank_run r ON r.run_id = f.run_id
    JOIN match_run m ON m.run_id = r.retrieve_run_id
    WHERE (%(direction)s::text IS NULL OR r.direction = %(direction)s)
    ORDER BY m.query_id, f.item_id, r.created_at DESC
)
SELECT kv.key AS feature,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY kv.value::float) AS median,
       count(*) AS n
FROM latest l
CROSS JOIN LATERAL jsonb_each_text(l.features_json) AS kv
WHERE kv.value IS NOT NULL AND NOT (l.missing_json ? kv.key)
GROUP BY kv.key
ORDER BY kv.key
"""


def feature_medians(conn: psycopg.Connection, direction: str | None = None) -> dict[str, tuple[float, int]]:
    """-> {feature: (trung vi, so cap)}."""
    rows = conn.execute(SQL, {"direction": direction}).fetchall()
    return {r["feature"]: (float(r["median"]), int(r["n"])) for r in rows}


def to_yaml(med: dict[str, tuple[float, int]], source: str) -> str:
    lines = [f"  cv_side_fixed:                  # trung vi tren {source} (cvmatch eval missing-defaults)"]
    lines += [f"    {f}: {v:.3f}                     # n = {n}" for f, (v, n) in med.items()]
    return "\n".join(lines)
