"""A4. Chuan hoa (thiet ke 04 A4).

- `anon_json` duoc sua TAI CHO: dia diem -> ma, `end` cua viec hien tai = thang nap, moi o chu
  qua `normalize` (NFC, chu thuong, bo trang tri, gop khoang trang; token bao ve giu nguyen).
- `anon_raw`: ban chi qua NFC (giu dau, hoa/thuong, ky tu gach dau dong) - nguon `text_raw` o A7,
  khong ghi DB.
- Co `no_diacritics` khi CV tieng Viet go khong dau.
- Thu tu moi -> cu cua kinh nghiem va du an (`item_order`), dung cho `item_idx` (0 = moi nhat).
"""

from __future__ import annotations

import copy
from typing import Any

from cvmatch.core.text.diacritics import no_diacritics
from cvmatch.core.text.normalize import nfc, normalize
from cvmatch.ingest.cv.record import CvContext, CvRecord


def _map_strings(obj: Any, fn) -> Any:
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_map_strings(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _map_strings(v, fn) for k, v in obj.items()}
    return obj


def recency_order(items: list[dict], ingest_ym: str) -> list[int]:
    """Chi so goc sap moi -> cu theo (end | thang nap neu dang lam, start). Khong co ngay -> cuoi."""
    dated, undated = [], []
    for i, it in enumerate(items):
        end = ingest_ym if it.get("is_current") else it.get("end")
        key = (end or it.get("start") or "", it.get("start") or "")
        (dated if key[0] else undated).append((key, i))
    dated.sort(key=lambda x: (x[0], -x[1]), reverse=True)  # hoa: giu thu tu goc
    return [i for _, i in dated] + [i for _, i in undated]


def free_texts(cv: dict) -> list[str]:
    """Cac o chu tu do (summary, description) - dung do ti le co dau."""
    out = []
    if isinstance(cv.get("summary"), str):
        out.append(cv["summary"])
    for sec in ("experiences", "projects"):
        for it in cv.get(sec) or []:
            d = it.get("description")
            if isinstance(d, str):
                out.append(d)
            elif isinstance(d, list):
                out.extend(x for x in d if isinstance(x, str))
    return out


def step_a04(rec: CvRecord, ctx: CvContext) -> CvRecord:
    anon = rec.anon_json or {}
    rec.anon_raw = _map_strings(copy.deepcopy(anon), nfc)

    norm = _map_strings(copy.deepcopy(anon), lambda s: normalize(s, keep_newlines=True))
    loc_code = ctx.locations(anon.get("location"))
    if anon.get("location") is not None:
        norm["location"] = loc_code or normalize(anon["location"])
    for sec in ("experiences", "projects"):
        for it in norm.get(sec) or []:
            if it.get("is_current"):
                it["end"] = ctx.ingest_ym
    rec.anon_json = norm
    rec.meta.location = loc_code

    rec.item_order = {
        "experience": recency_order(norm.get("experiences") or [], ctx.ingest_ym),
        "project": recency_order(norm.get("projects") or [], ctx.ingest_ym),
    }

    if no_diacritics(free_texts(rec.anon_raw), ctx.cfg.prep.no_diacritics.threshold):
        rec.add_flag("no_diacritics")
    return rec
