"""Chi so danh gia (thiet ke 09 muc 1, 3.1, 4.1). Ham thuan, khong DB.

- Retrieve: Recall@K (K = 50/100/200/300) tren MOI muc phu hop da cham cua truy van.
- Rerank: tinh trong so muc phu hop CO MAT trong pool (~200):
  nDCG@10 (gain = 2^nhan - 1, chiet khau log2), Recall@N, Recall@N / min(N, so phu hop).
- AUC muc cap (R_ij phan biet `khop` voi `khong`), hoa tinh 0,5.
- Tong hop: trung binh theo truy van, truy van te nhat, tach theo nhom; ti le cap chua cham.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence


def relevant(labels: Mapping[str, int], min_grade: int = 1) -> set[str]:
    return {k for k, g in labels.items() if g >= min_grade}


def recall_at_k(ranked: Sequence[str], labels: Mapping[str, int], k: int, *, min_grade: int = 1,
                universe: Iterable[str] | None = None) -> float | None:
    """Ti le muc phu hop nam trong top k. `universe`: chi tinh muc phu hop thuoc tap nay (vd pool rerank).
    Khong co muc phu hop -> None (truy van khong duoc tinh vao trung binh)."""
    rel = relevant(labels, min_grade)
    if universe is not None:
        rel &= set(universe)
    if not rel:
        return None
    return len(rel & set(ranked[:k])) / len(rel)


def recall_at_k_norm(ranked: Sequence[str], labels: Mapping[str, int], k: int, *, min_grade: int = 1,
                     universe: Iterable[str] | None = None) -> float | None:
    """Recall@k / min(k, so phu hop): = 1 khi top k chua het muc phu hop co the chua."""
    rel = relevant(labels, min_grade)
    if universe is not None:
        rel &= set(universe)
    if not rel:
        return None
    return len(rel & set(ranked[:k])) / min(k, len(rel))


def dcg(gains: Sequence[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked: Sequence[str], labels: Mapping[str, int], k: int = 10, *,
              universe: Iterable[str] | None = None) -> float | None:
    """gain = 2^nhan - 1; muc chua cham = 0. Ly tuong: sap cac nhan (trong `universe` neu co) giam dan."""
    pool = set(universe) if universe is not None else None
    ideal_grades = sorted((g for c, g in labels.items() if g > 0 and (pool is None or c in pool)), reverse=True)
    if not ideal_grades:
        return None
    gain = lambda g: (2 ** g) - 1  # noqa: E731
    actual = dcg([gain(labels.get(c, 0)) for c in ranked[:k]])
    ideal = dcg([gain(g) for g in ideal_grades[:k]])
    return actual / ideal if ideal > 0 else None


def auc(scores: Sequence[float], positive: Sequence[bool]) -> float | None:
    """AUC = P(diem duong > diem am), hoa 0,5 (Mann-Whitney)."""
    pos = [s for s, p in zip(scores, positive) if p]
    neg = [s for s, p in zip(scores, positive) if not p]
    if not pos or not neg:
        return None
    # theo hang de O(n log n)
    allv = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    rank_sum, i, n = 0.0, 0, len(allv)
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        rank_sum += avg * sum(1 for t in range(i, j + 1) if allv[t][1] == 1)
        i = j + 1
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def unjudged_rate(ranked: Sequence[str], labels: Mapping[str, int], k: int) -> float | None:
    top = list(ranked[:k])
    if not top:
        return None
    return sum(1 for c in top if c not in labels) / len(top)


def summarize(per_query: Mapping[str, float | None], groups: Mapping[str, str] | None = None) -> dict:
    """{mean, worst, worst_query, n, by_group: {nhom: mean}} - bo truy van None."""
    vals = {q: v for q, v in per_query.items() if v is not None}
    if not vals:
        return {"mean": None, "worst": None, "worst_query": None, "n": 0, "by_group": {}}
    worst_q = min(vals, key=lambda q: (vals[q], q))
    out = {"mean": sum(vals.values()) / len(vals), "worst": vals[worst_q], "worst_query": worst_q, "n": len(vals),
           "by_group": {}}
    if groups:
        acc: dict[str, list[float]] = defaultdict(list)
        for q, v in vals.items():
            acc[groups.get(q) or "?"].append(v)
        out["by_group"] = {g: sum(x) / len(x) for g, x in sorted(acc.items())}
    return out
