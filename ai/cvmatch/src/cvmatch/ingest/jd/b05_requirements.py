"""B5. Yeu cau dang metadata + phan loai tung dong yeu cau (thiet ke 05 B5).

`kind` cua mot dong (thu tu uu tien): years -> degree -> language -> skill_only -> text.
- `skill_only`: sau khi bo cac ky nang LOAI `technology` da gan ma va cac tu noi ("thành thạo",
  "và"...) thi khong con gi. Ky nang loai `concept` KHONG bi bo: "Hiểu biết về microservices" la
  yeu cau ve hieu biet -> `text` (cham bang BERTScore, feature B5) - khop vi du cua thiet ke.
"""

from __future__ import annotations

import re

from cvmatch.core.text.normalize import normalize, to_raw
from cvmatch.ingest.jd.record import JdRecord, PrepContext, RequirementItem

_NUM = r"(\d+(?:[.,]\d+)?)"
_YEARS_WORD = r"(?:năm|nam|years?|yrs?)"
_RANGE_RE = re.compile(rf"(?:từ\s*)?{_NUM}\s*(?:-|–|—|~|đến|to)\s*{_NUM}\+?\s*{_YEARS_WORD}")
_MIN_RE = re.compile(
    rf"(?:tối thiểu|ít nhất|trên|hơn|từ|at least|minimum|min|over|more than)\s*{_NUM}\+?\s*{_YEARS_WORD}"
    rf"|{_NUM}\s*\+\s*{_YEARS_WORD}"
    rf"|{_NUM}\s*{_YEARS_WORD}\s*(?:kinh nghiệm|kn|experience|làm việc)")
_YEARS_KIND_RE = re.compile(rf"\d\s*\+?\s*{_YEARS_WORD}.*?(?:kinh nghiệm|experience|làm việc)"
                            rf"|(?:kinh nghiệm|experience).*?\d\s*\+?\s*{_YEARS_WORD}")
_DEGREE_RE = re.compile(r"tốt nghiệp|bằng (?:cấp|đại học|cao đẳng|cử nhân|kỹ sư)|đại học|cao đẳng|"
                        r"cử nhân|thạc sĩ|degree|bachelor|master'?s?|graduated")
_IT_MAJOR_RE = re.compile(r"cntt|công nghệ thông tin|khoa học máy tính|kỹ thuật phần mềm|"
                          r"\bit\b|computer science|software engineering|liên quan|related")
_LANG_RE = re.compile(r"tiếng (?:anh|nhật|hàn|trung|pháp|đức)|toeic|ielts|toefl|jlpt|topik|hsk|"
                      r"\benglish\b|japanese|ngoại ngữ")
_FILLER = {
    "thành", "thạo", "sử", "dụng", "tốt", "có", "kinh", "nghiệm", "làm", "việc", "với", "và", "hoặc",
    "hay", "các", "công", "nghệ", "ngôn", "ngữ", "framework", "frameworks", "lập", "trình", "như", "là",
    "một", "lợi", "thế", "ưu", "tiên", "biết", "nắm", "vững", "về", "trong", "cơ", "bản", "tối",
    "thiểu", "ít", "nhất", "ít", "nhiều", "cao", "khả", "năng", "được", "đã", "từng", "quen", "thuộc",
    "proficient", "in", "with", "and", "or", "experience", "experienced", "knowledge", "of", "using",
    "good", "strong", "familiar", "plus", "is", "a", "the", "skills", "skill", "tools", "etc",
}
_WORD_RE = re.compile(r"[^\W\d_]+|\d+", re.UNICODE)


def parse_years(text: str) -> tuple[float | None, float | None]:
    """'tối thiểu 4 năm' -> (4, None); '3–5 năm' -> (3, 5); '2+ years' -> (2, None)."""
    t = normalize(text)
    m = _RANGE_RE.search(t)
    if m:
        a, b = (float(x.replace(",", ".")) for x in m.groups())
        return min(a, b), max(a, b)
    m = _MIN_RE.search(t)
    if m:
        val = next(g for g in m.groups() if g)
        return float(val.replace(",", ".")), None
    return None, None


def classify(text_norm: str, ctx: PrepContext) -> str:
    if _YEARS_KIND_RE.search(text_norm):
        return "years"
    if _DEGREE_RE.search(text_norm):
        return "degree"
    if _LANG_RE.search(text_norm):
        return "language"
    matches = ctx.matcher.find(text_norm)
    tech = [mt for mt in matches if ctx.snapshot.skills[mt.skill_id].type == "technology"]
    if tech:
        rest = text_norm
        for mt in sorted(tech, key=lambda x: x.start, reverse=True):
            rest = rest[:mt.start] + " " + rest[mt.end:]
        if all(w in _FILLER for w in _WORD_RE.findall(rest)):
            return "skill_only"
    return "text"


def step_b05(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    raw, norm = rec.raw_json, rec.norm_json or {}
    items = []
    for line in raw.get("requirements") or []:
        text_raw = to_raw(line, keep_newlines=False)
        if not text_raw:
            continue
        text = normalize(text_raw)
        items.append(RequirementItem(idx=len(items), text=text, text_raw=text_raw, kind=classify(text, ctx)))
    rec.requirement_items = items

    meta = rec.meta
    meta.location = norm.get("location") if raw.get("location") else None
    meta.work_mode = norm.get("work_mode") or None
    meta.min_years, meta.max_years = raw.get("min_years"), raw.get("max_years")
    if meta.min_years is None or meta.max_years is None:
        for it in items:
            if it.kind != "years":
                continue
            lo, hi = parse_years(it.text)
            if meta.min_years is None and lo is not None:
                meta.min_years = lo
            if meta.max_years is None and hi is not None:
                meta.max_years = hi
    level, role, _ = ctx.lookup.parse_title(raw.get("title"))
    if raw.get("level"):
        lv, _ = ctx.lookup.split_title(raw["level"])
        level = lv if lv is not None else level
    meta.level_rank = level
    meta.role_group = raw.get("role_group") or role

    edu = normalize(raw.get("edu_required") or "") or None
    if edu in ("none", "it_related", "any_degree"):
        meta.edu_required = edu
    else:
        degree_lines = [it.text for it in items if it.kind == "degree"]
        if degree_lines:
            meta.edu_required = "it_related" if any(_IT_MAJOR_RE.search(t) for t in degree_lines) else "any_degree"
    return rec
