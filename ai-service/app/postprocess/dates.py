"""Chronology check for experience / project dates (feature 011).

Timeline layouts print the end date above the start date ("03/2025 ... 06/2024"), and the model
then reads them in visual order. When both dates parse and start is later than end, swap them.
Values stay verbatim (only their order changes); anything unparseable is left untouched.
"""

from __future__ import annotations

import re
from typing import Any

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_month(value: Any) -> int | None:
    """'03/2025', '3-2025', 'Mar 2025', 'March 2025', 'T3/2025', 'Tháng 3/2025', '2025' -> year * 12 + month."""
    if not isinstance(value, str) or not value.strip():
        return None
    v = value.strip().lower()
    m = re.search(r"(?:th[aá]ng\s*|t)?(\d{1,2})\s*[/.\-]\s*(\d{4})", v)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(2)) * 12 + int(m.group(1))
    m = re.search(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", v)
    if m and m.group(1) in _MONTHS:
        return int(m.group(2)) * 12 + _MONTHS[m.group(1)]
    m = re.fullmatch(r"(\d{4})", v)
    if m:
        return int(m.group(1)) * 12 + 1
    return None


def fix_date_order(profile: dict, stats: Any = None) -> dict:
    for section in ("experience", "personal_projects"):
        for item in profile.get(section) or []:
            if not isinstance(item, dict):
                continue
            start, end = parse_month(item.get("start_date")), parse_month(item.get("end_date"))
            if start is not None and end is not None and start > end:
                item["start_date"], item["end_date"] = item["end_date"], item["start_date"]
                if stats is not None:
                    stats.dates_swapped = getattr(stats, "dates_swapped", 0) + 1
    return profile
