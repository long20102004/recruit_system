"""Bo nhan chung cho Retrieve va Rerank (thiet ke 09 muc 2).

Dinh dang file (CSV UTF-8, co dong tieu de):

1. Nhan muc (truy van, muc) - `graded.csv`:
       query_id,item_id,grade,rater[,note]
   - Luong C: query_id = jd_id, item_id = cv_id. Luong D: query_id = cv_id, item_id = jd_id.
   - grade in {0, 1, 2}: 0 khong phu hop, 1 mot phan, 2 phu hop. Moi cap 2 nguoi cham (`rater` khac nhau);
     ban da thong nhat ghi them mot dong `rater = final` (thao luan / nguoi thu ba).
   - Nhan cuoi: `final` neu co; khong thi cac nguoi cham trung nhau -> gia tri do; lech -> lam tron XUONG
     trung binh (than trong) va dem vao `n_disagree`.
2. Nhan muc cap cau (trach nhiem x gach) - `pairs.csv`:
       pair_id,jd_text,cv_text,label,rater[,jd_id,resp_idx,cv_id,evidence_id]
   - label in {khop, mot_phan, khong}. Co san van ban de hieu chuan khong can DB.

Chia dev/test 50/50 phan tang theo nhom vai tro (seed co dinh). Moi tinh chinh chi lam tren dev.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

GRADED_COLS = ("query_id", "item_id", "grade", "rater")
PAIR_COLS = ("pair_id", "jd_text", "cv_text", "label", "rater")
PAIR_LABELS = ("khop", "mot_phan", "khong")


@dataclass
class GradedLabels:
    by_rater: dict[str, dict[tuple[str, str], int]] = field(default_factory=dict)
    final: dict[tuple[str, str], int] = field(default_factory=dict)
    n_disagree: int = 0

    def for_query(self, q: str) -> dict[str, int]:
        return {i: g for (qq, i), g in self.final.items() if qq == q}

    @property
    def queries(self) -> list[str]:
        return sorted({q for q, _ in self.final})

    def raters(self) -> list[str]:
        return sorted(r for r in self.by_rater if r != "final")


def _resolve(by_rater: dict[str, dict[tuple[str, str], int]]) -> tuple[dict, int]:
    final: dict[tuple[str, str], int] = dict(by_rater.get("final", {}))
    votes: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r, d in by_rater.items():
        if r == "final":
            continue
        for k, g in d.items():
            votes[k].append(g)
    dis = 0
    for k, gs in votes.items():
        if k in final:
            continue
        if len(set(gs)) > 1:
            dis += 1
        final[k] = int(sum(gs) // len(gs)) if len(set(gs)) > 1 else gs[0]
    return final, dis


def load_graded(path: str | Path) -> GradedLabels:
    by: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
    with Path(path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            g = int(row["grade"])
            if g not in (0, 1, 2):
                raise ValueError(f"grade phai thuoc 0/1/2: {row}")
            by[row.get("rater") or "r1"][(row["query_id"], row["item_id"])] = g
    final, dis = _resolve(by)
    return GradedLabels(dict(by), final, dis)


def write_graded(path: str | Path, rows: Iterable[tuple[str, str, int, str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(GRADED_COLS)
        w.writerows(rows)


@dataclass
class PairLabel:
    pair_id: str
    jd_text: str
    cv_text: str
    label: str
    extra: dict = field(default_factory=dict)


def load_pairs(path: str | Path) -> list[PairLabel]:
    """Nhan cap cau. Nhieu nguoi cham: `final` > da so > than trong (nhan thap hon)."""
    rows: dict[str, list[dict]] = defaultdict(list)
    with Path(path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["label"] not in PAIR_LABELS:
                raise ValueError(f"label phai thuoc {PAIR_LABELS}: {row}")
            rows[row["pair_id"]].append(row)
    out = []
    order = {lab: i for i, lab in enumerate(PAIR_LABELS)}      # khop < mot_phan < khong (than trong = lon)
    for pid, rs in rows.items():
        fin = [r for r in rs if r.get("rater") == "final"]
        if fin:
            lab = fin[0]["label"]
        else:
            cnt: dict[str, int] = defaultdict(int)
            for r in rs:
                cnt[r["label"]] += 1
            lab = max(cnt, key=lambda x: (cnt[x], order[x]))
        r0 = rs[0]
        out.append(PairLabel(pid, r0["jd_text"], r0["cv_text"], lab,
                             {k: v for k, v in r0.items() if k not in PAIR_COLS}))
    return sorted(out, key=lambda p: p.pair_id)


# --------------------------------------------------------------------------- do dong thuan


def cohen_kappa(a: Mapping[tuple, int], b: Mapping[tuple, int], *, weights: str | None = None,
                categories: Iterable[int] = (0, 1, 2)) -> float | None:
    """kappa Cohen tren cac cap ca hai cung cham. `weights='quadratic'` -> kappa co trong so (thang thu tu)."""
    keys = [k for k in a if k in b]
    cats = list(categories)
    if not keys:
        return None
    n, m = len(keys), len(cats)
    pos = {c: i for i, c in enumerate(cats)}
    obs = [[0.0] * m for _ in range(m)]
    for k in keys:
        obs[pos[a[k]]][pos[b[k]]] += 1
    ra = [sum(obs[i]) for i in range(m)]
    rb = [sum(obs[i][j] for i in range(m)) for j in range(m)]
    w = [[(0.0 if i == j else 1.0) if weights is None else ((i - j) ** 2) / ((m - 1) ** 2) for j in range(m)]
         for i in range(m)]
    po = sum(w[i][j] * obs[i][j] for i in range(m) for j in range(m)) / n
    pe = sum(w[i][j] * ra[i] * rb[j] for i in range(m) for j in range(m)) / (n * n)
    if pe == 0:
        return 1.0 if po == 0 else None
    return 1.0 - po / pe


def kappa_report(labels: GradedLabels) -> dict:
    rs = labels.raters()
    out = {"raters": rs, "n_disagree": labels.n_disagree}
    if len(rs) >= 2:
        a, b = labels.by_rater[rs[0]], labels.by_rater[rs[1]]
        out.update(kappa=cohen_kappa(a, b), kappa_quadratic=cohen_kappa(a, b, weights="quadratic"),
                   n_common=len([k for k in a if k in b]))
    return out


# --------------------------------------------------------------------------- chia dev / test


def split_dev_test(queries: Mapping[str, str | None], *, seed: int = 13, dev_ratio: float = 0.5) -> dict[str, str]:
    """{query_id: nhom vai tro} -> {query_id: 'dev'|'test'}, phan tang theo nhom, tat dinh theo seed.
    Nhom le: phan du luan phien dev/test theo thu tu nhom (khong lech ve mot phia)."""
    by: dict[str, list[str]] = defaultdict(list)
    for q, g in queries.items():
        by[g or "?"].append(q)
    rng = random.Random(seed)
    out: dict[str, str] = {}
    extra_to_dev = True
    for g in sorted(by):
        qs = sorted(by[g])
        rng.shuffle(qs)
        n_dev = int(len(qs) * dev_ratio)
        if len(qs) * dev_ratio - n_dev > 1e-9:
            n_dev += int(extra_to_dev)
            extra_to_dev = not extra_to_dev
        for i, q in enumerate(qs):
            out[q] = "dev" if i < n_dev else "test"
    return out
