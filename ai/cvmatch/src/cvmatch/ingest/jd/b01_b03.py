"""B1 kiem schema + cap version, B2 chuan hoa (CUNG ham A4), B3 chon phan de match -> query_text."""

from __future__ import annotations

import copy
from typing import Any

from cvmatch.core.text.normalize import normalize
from cvmatch.ingest.cv.a04_normalize import _map_strings
from cvmatch.ingest.jd.record import JdRecord, JdVersionLookup, PrepContext, UnchangedJD
from cvmatch.ingest.jd.schema import _as_list, adapt_jd, validate_jd

_STATUSES = {"open", "draft", "closed", "expired"}
_STATUS_ALIASES = {"active": "open", "published": "open", "mở": "open", "đang tuyển": "open",
                   "đóng": "closed", "inactive": "closed", "hết hạn": "expired"}
QUERY_LABELS = ("Chức danh", "Kỹ năng", "Yêu cầu", "Trách nhiệm")


def skill_name(s: Any) -> str:
    return s.get("name", "") if isinstance(s, dict) else str(s)


def step_b01(raw: Any, ctx: PrepContext, versions: JdVersionLookup | None) -> JdRecord:
    adapted = adapt_jd(copy.deepcopy(raw))
    jd_in = validate_jd(adapted)  # InvalidJD
    data = dict(adapted)  # JSON goc (sau adapter); chi dua truong danh sach ve mang
    for key in ("skills", "requirements", "responsibilities", "benefits"):
        if key in data:
            data[key] = _as_list(data[key])
    jd_id = str(jd_in.jd_id)
    status = normalize(jd_in.status or "open")
    status = _STATUS_ALIASES.get(status, status)
    if status not in _STATUSES:
        status = "open"
    version = 1
    if versions is not None:
        prev = versions.latest(jd_id)
        if prev is not None:
            if prev[1] == data:
                raise UnchangedJD(jd_id, prev[0])
            version = prev[0] + 1
    rec = JdRecord(jd_id=jd_id, version=version, status=status, raw_json=data)
    rec.ontology_version = ctx.snapshot.ontology_version
    rec.pipeline_version = ctx.cfg.prep.version
    return rec


def step_b02(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    norm = _map_strings(copy.deepcopy(rec.raw_json), normalize)
    if rec.raw_json.get("location"):
        norm["location"] = ctx.locations(rec.raw_json["location"]) or norm["location"]
    rec.norm_json = norm
    return rec


def query_parts(norm: dict) -> dict[str, str]:
    """Noi dung tung dong cua van ban truy van (khong nhan). company_intro, benefits... KHONG vao."""
    return {
        "Chức danh": norm.get("title") or "",
        "Kỹ năng": ", ".join(n for n in (skill_name(s) for s in norm.get("skills") or []) if n),
        "Yêu cầu": ". ".join(r for r in norm.get("requirements") or [] if r),
        "Trách nhiệm": ". ".join(r for r in norm.get("responsibilities") or [] if r),
    }


def step_b03(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    parts = query_parts(rec.norm_json or {})
    rec.query_text = "\n".join(f"{lab}: {parts[lab]}" for lab in QUERY_LABELS if parts[lab])
    return rec
