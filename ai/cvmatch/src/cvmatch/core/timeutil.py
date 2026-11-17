"""Tien ich thang `YYYY-MM` dung chung (A6 years_experience, Rerank B1/B2).

Quy uoc dem thang (chot o T04, khop ca hai vi du cua thiet ke 04 A6):
- moi muc phu cac thang tu `start` den `end`, TINH CA HAI DAU;
- muc dang lam (`is_current`): `end` = thang nap CV nhung thang nay CHUA tron nen khong tinh.
  -> 2022-03 .. hien tai (nap 2026-11) = 56 thang = 4,7 nam; 2019-01..2020-06 + 2020-03..2022-12 = 48 thang.
"""

from __future__ import annotations

from collections.abc import Iterable


def ym_to_index(ym: str) -> int:
    y, m = ym.split("-")
    return int(y) * 12 + int(m) - 1


def index_to_ym(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def add_months(ym: str, n: int) -> str:
    return index_to_ym(ym_to_index(ym) + n)


def month_span(start: str | None, end: str | None, *, is_current: bool = False) -> range | None:
    """Tap thang (chi so) ma mot muc phu. Thieu start/end -> None. end < start -> None."""
    if not start or not end:
        return None
    s, e = ym_to_index(start), ym_to_index(end)
    if is_current:
        e -= 1
    if e < s:
        return None
    return range(s, e + 1)


def count_months(spans: Iterable[range | None]) -> int:
    """So thang cua hop cac khoang (gop chong lan)."""
    months: set[int] = set()
    for sp in spans:
        if sp is not None:
            months.update(sp)
    return len(months)
