"""A6. Trich metadata (thiet ke 04 A6). Thieu du lieu -> None, khong doan.

- `years_experience`: hop cac khoang thoi gian cua muc `job` (gop chong lan, quy uoc dem thang o
  `core/timeutil.py`); KHONG lay con so tu ghi trong summary. Thuc tap tinh rieng `intern_months`.
  Muc thieu `start` (hoac thieu `end` ma khong dang lam) -> khong tinh, co `years_uncertain`.
- `role_group` tung muc: tra `role_title_map` theo chuc danh (`rule`) -> khong ra thi dem tu khoa
  theo nhom trong cac gach cua muc (`keyword`, nhan nhom dau neu >= ratio x nhom thu hai) -> None.
- `level_rank`: tu cap bac trong chuc danh gan nhat (`title`); khong co thi suy tu so nam
  (`inferred`, bang `prep.level_from_years`).
"""

from __future__ import annotations

import re

from cvmatch.core.text.normalize import normalize
from cvmatch.core.timeutil import add_months, count_months, month_span, ym_to_index
from cvmatch.ingest.cv.bullets import split_description
from cvmatch.ingest.cv.record import CvContext, CvRecord, EducationRow, ExperienceRow

def months_between(a: str, b: str) -> int:
    return ym_to_index(b) - ym_to_index(a)


_STUDYING_RE = re.compile(r"đang học|dang hoc|studying|sinh viên năm|in progress|expected")


def _keyword_res(ctx: CvContext) -> dict[str, re.Pattern]:
    cache = ctx.extra.get("_role_kw_re")
    if cache is None:
        cache = {
            g: re.compile(r"(?<![\w.#+])(?:" + "|".join(re.escape(k) for k in sorted(kws, key=len, reverse=True))
                          + r")(?![\w+#])")
            for g, kws in ctx.role_keywords.items() if kws
        }
        ctx.extra["_role_kw_re"] = cache
    return cache


def role_by_keywords(text: str, ctx: CvContext) -> tuple[str | None, float | None]:
    counts = sorted(((len(r.findall(text)), g) for g, r in _keyword_res(ctx).items()), reverse=True)
    if not counts or counts[0][0] == 0:
        return None, None
    top, second = counts[0][0], (counts[1][0] if len(counts) > 1 else 0)
    if top >= ctx.cfg.prep.experience.role_keyword_ratio * second:
        return counts[0][1], round(top / (top + second), 2)
    return None, None


def _exp_kind(section: str, item: dict, title_level: int | None) -> str:
    kind = normalize(str(item.get("kind") or ""))
    if section == "experience":
        if "intern" in kind or "thực tập" in kind or title_level == 0:
            return "intern"
        return "job"
    if "team" in kind or "nhóm" in kind:
        return "project_team"
    if "personal" in kind or "cá nhân" in kind:
        return "project_personal"
    ts = item.get("team_size")
    return "project_team" if isinstance(ts, int) and ts > 1 else "project_personal"


def _dates_quality(rec: CvRecord, key: str, src: int, item: dict) -> str:
    if not item.get("start"):
        return "missing"
    if not item.get("end") and not item.get("is_current"):
        return "partial"
    if f"{key}[{src}].start" in rec.date_year_only or f"{key}[{src}].end" in rec.date_year_only:
        return "partial"
    return "ok"


def _infer_level(years: float | None, table: list[tuple[float, int]]) -> int | None:
    if years is None:
        return None
    level = None
    for min_years, rank in table:
        if years >= min_years:
            level = rank
    return level


def step_a06(rec: CvRecord, ctx: CvContext) -> CvRecord:
    cv = rec.anon_json or {}
    cv_raw = rec.anon_raw or {}
    min_words = ctx.cfg.prep.bullet.min_words
    rows: list[ExperienceRow] = []

    for section, key in (("experience", "experiences"), ("project", "projects")):
        items = cv.get(key) or []
        for idx, src in enumerate(rec.item_order.get(section, [])):
            item = items[src]
            title = item.get("title") if section == "experience" else (item.get("role") or item.get("name"))
            level, role, _ = ctx.lookup.parse_title(title) if title else (None, None, "")
            conf, role_src = (1.0, "rule") if role else (None, None)
            if role is None:
                desc = " ".join(normalize(p.raw) for p in
                                split_description(cv_raw[key][src].get("description"), min_words))
                role, conf = role_by_keywords(desc, ctx)
                role_src = "keyword" if role else None
            is_current = bool(item.get("is_current"))
            span = month_span(item.get("start"), item.get("end"), is_current=is_current)
            rows.append(ExperienceRow(
                idx=idx, src_index=src, section=section,
                kind=_exp_kind(section, item, level if section == "experience" else None),
                title_raw=title, role_group=role, role_group_conf=conf, role_group_src=role_src,
                start_ym=item.get("start"), end_ym=item.get("end"), is_current=is_current,
                months=len(span) if span is not None else None,
                dates_quality=_dates_quality(rec, key, src, item),
            ))
    rec.experiences = rows

    # ---- so nam kinh nghiem (chi muc job), thuc tap tinh rieng
    jobs = [r for r in rows if r.kind == "job"]
    interns = [r for r in rows if r.kind == "intern"]
    spans = {id(r): month_span(r.start_ym, r.end_ym, is_current=r.is_current) for r in jobs + interns}
    if any(spans[id(r)] is None for r in jobs + interns):
        rec.add_flag("years_uncertain")
    job_spans = [spans[id(r)] for r in jobs if spans[id(r)] is not None]
    if not jobs:
        years = 0.0
    elif job_spans:
        years = round(count_months(job_spans) / 12, 1)
    else:
        years = None
    rec.meta.years_experience = years
    rec.meta.intern_months = count_months(spans[id(r)] for r in interns)

    # ---- nhom vai tro + cap bac tu chuc danh gan nhat
    recent = next((r for r in rows if r.section == "experience"), None)
    if recent is not None:
        rec.meta.role_group = recent.role_group
        level, _ = ctx.lookup.split_title(recent.title_raw)
        if level is not None:
            rec.meta.level_rank, rec.meta.level_source = level, "title"
    if rec.meta.level_rank is None:
        inferred = _infer_level(years if jobs else None, ctx.cfg.prep.level_from_years)
        if inferred is not None:
            rec.meta.level_rank, rec.meta.level_source = inferred, "inferred"

    # ---- hoc van (khong luu ten truong)
    edu_items = cv.get("education") or []
    order = sorted(range(len(edu_items)), key=lambda i: edu_items[i].get("end") or "", reverse=True)
    edu_rows: list[EducationRow] = []
    for idx, src in enumerate(order):
        e = edu_items[src]
        end = e.get("end")
        status_text = " ".join(str(e.get(k) or "") for k in ("status", "end_raw"))
        expected = end
        if _STUDYING_RE.search(status_text) or (end and end > rec.ingest_ym):
            status = "studying"
        elif end:
            status = "graduated"
        elif (ec := ctx.cfg.prep.education) and (start := e.get("start")) and                 months_between(start, rec.ingest_ym) <= 12 * ec.max_study_years:
            # V-07: Module 1 khong co truong "dang hoc"; nam bat dau gan, chua co nam ket thuc -> dang hoc
            status, expected = "studying", add_months(start, 12 * ec.default_duration_years)
            rec.add_flag("edu_end_inferred")
        else:
            status = "unknown"
        major = e.get("major")
        edu_rows.append(EducationRow(
            idx=idx, level=e.get("level"), major_raw=major,
            major_group=ctx.lookup.major_group_of(major) if major else None,
            status=status, end_year=int(end[:4]) if end else None,
            expected_end_ym=expected if status == "studying" else None,
        ))
    rec.education = edu_rows
    rec.meta.major_group = next((r.major_group for r in edu_rows if r.major_group), None)
    return rec
