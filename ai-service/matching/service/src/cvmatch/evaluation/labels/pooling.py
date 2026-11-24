"""Chon muc de cham bang gop (pooling, thiet ke 09 muc 2).

Hop cua top-300 Retrieve cua MOI cau hinh RT-*, top-60 Rerank cua MOI cau hinh R-*, va 20 muc ngau nhien
tu phan con lai cua kho -> danh sach can cham (CSV cho nguoi cham, kem cot nguon de biet vi sao duoc chon).
Cap da cham roi (file nhan cu) duoc bo qua.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path


def pool_items(runs: dict[str, dict[str, list[str]]], all_items: list[str], *, n_random: int = 20, seed: int = 13,
               already: set[tuple[str, str]] | None = None) -> dict[str, dict[str, list[str]]]:
    """`runs`: {ten_cau_hinh: {query_id: [item da cat top]}} -> {query_id: {item_id: [nguon]}}."""
    rng = random.Random(seed)
    out: dict[str, dict[str, list[str]]] = defaultdict(dict)
    queries = sorted({q for r in runs.values() for q in r})
    for q in queries:
        for name, r in runs.items():
            for it in r.get(q, []):
                out[q].setdefault(it, []).append(name)
        rest = sorted(set(all_items) - set(out[q]))
        for it in rng.sample(rest, min(n_random, len(rest))):
            out[q].setdefault(it, []).append("random")
        if already:
            for it in [i for i in out[q] if (q, i) in already]:
                del out[q][it]
    return dict(out)


def write_pool_csv(path: str | Path, pooled: dict[str, dict[str, list[str]]], *, raters: tuple[str, ...] = ("r1", "r2"),
                   describe=None) -> int:
    """Mot dong cho moi (truy van, muc, nguoi cham), cot grade de trong. `describe(q, i)` -> mo ta ngan."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "item_id", "grade", "rater", "sources", "note"])
        for q in sorted(pooled):
            for it in sorted(pooled[q]):
                for r in raters:
                    w.writerow([q, it, "", r, "|".join(sorted(set(pooled[q][it]))), describe(q, it) if describe else ""])
                    n += 1
    return n
