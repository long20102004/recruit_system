"""A1. Nhan JSON va kiem tra schema (thiet ke 04 A1)."""

from __future__ import annotations

import copy
import uuid
from typing import Any

import re

from cvmatch.core.text.normalize import is_present, is_year_only, normalize, parse_ym
from cvmatch.ingest.cv.adapter import adapt_cv
from cvmatch.ingest.cv.record import CvContext, CvRecord
from cvmatch.ingest.cv.schema import validate_cv

DATED_SECTIONS = ("experiences", "projects", "education")
_STUDYING_RE = re.compile(r"đang học|dang hoc|studying|expected")


def _fix_dates(cv: dict, flags: list[str], year_only: list[str]) -> None:
    """Sua ngay ve YYYY-MM tai cho. Khong doc duoc -> None + co `date_unparsed`.
    "hiện tại"/"present" o `end` -> is_current = True, end = None."""
    for sec in DATED_SECTIONS:
        for i, item in enumerate(cv.get(sec) or []):
            if not isinstance(item, dict):
                continue
            for key in ("start", "end"):
                v = item.get(key)
                if v is None or v == "":
                    item[key] = None
                    continue
                if key == "end" and (is_present(str(v)) or
                                     (sec == "education" and _STUDYING_RE.search(normalize(str(v))))):
                    item["end"] = None
                    if sec == "education":
                        item.setdefault("status", "đang học")
                    else:
                        item["is_current"] = True
                    continue
                ym = parse_ym(v, role=key)
                if ym is None:
                    item[key] = None
                    if "date_unparsed" not in flags:
                        flags.append("date_unparsed")
                else:
                    if is_year_only(v):
                        year_only.append(f"{sec}[{i}].{key}")
                    item[key] = ym


def step_a01(raw_input: Any, ctx: CvContext) -> CvRecord:
    """-> CvRecord voi cv_id, raw_json (da adapter + sua ngay), flags.

    Sai schema -> raise InvalidCV (caller ghi ingest_log, khong tao dong `cv`).
    """
    adapted = (adapt_cv(copy.deepcopy(raw_input), null_end_current=ctx.cfg.prep.experience.null_end_current)
               if isinstance(raw_input, dict) else raw_input)
    validate_cv(adapted)  # chi kiem kieu; du lieu tiep tuc o dang dict de giu truong la

    flags: list[str] = []
    year_only: list[str] = []
    cv = copy.deepcopy(adapted)
    for key in ("skills", "experiences", "projects", "education", "certificates", "languages"):
        if cv.get(key) is None:
            cv[key] = []
    _fix_dates(cv, flags, year_only)

    if not cv["experiences"] and not cv["projects"] and not cv["skills"]:
        flags.append("low_content")

    rec = CvRecord(cv_id=str(uuid.uuid4()), ingest_ym=ctx.ingest_ym, raw_json=cv, flags=flags,
                   date_year_only=year_only)
    rec.ontology_version = ctx.snapshot.ontology_version
    rec.pipeline_version = ctx.cfg.prep.version
    return rec
