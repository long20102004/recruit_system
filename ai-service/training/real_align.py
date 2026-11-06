"""Align old labels of real CVs to their PDFBox text and apply v3 label conventions (feature 007).

Old real-CV labels were made on another text extraction, so values can differ from the
serving text ("English B1 (2024)" vs "English B1 2024"). Every string value is snapped to
the exact span of the PDFBox text (fuzzy >= 85, same matcher as post-processing) or dropped.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from typing import Any

from app.postprocess.schema import normalize_profile
from app.postprocess.skills import clean_skill_list
from app.postprocess.text_match import find_span, normalize_with_map

# Spoken-language check: programming languages must never be labelled as languages (v3).
PROGRAMMING = {
    "java", "javascript", "typescript", "python", "c", "c++", "c#", "csharp", "go", "golang", "php",
    "ruby", "kotlin", "swift", "dart", "rust", "scala", "sql", "html", "html5", "css", "css3", "r",
    "perl", "objective-c", "vb.net", "shell", "bash", "lua", "matlab", "solidity",
}
# "Company, Ho Chi Minh City" / "Company – Tan Binh, HCM": the part after the separator is a location.
_LOCATION = re.compile(
    r"\s*(?:,|–|-|—|\|)\s*(?:[A-ZĐ][\w\s.]*?)?(?:city|district|ward|ha noi|hà nội|hanoi|hcm|ho chi minh|"
    r"hồ chí minh|da nang|đà nẵng|vietnam|việt nam|nha trang|can tho|cần thơ|hai phong|hải phòng|"
    r"phu nhuan|tan binh|thu duc)\b.*$",
    re.IGNORECASE,
)


def is_programming_language(name: str | None) -> bool:
    key = re.sub(r"\s*\(.*\)$", "", (name or "").strip()).lower()
    return key in PROGRAMMING


def strip_location(company: str) -> str:
    cut = _LOCATION.sub("", company).strip(" ,–-|")
    return cut or company


_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"]


def date_candidates(value: str) -> list[str]:
    """Verbatim spellings a normalised "MM/YYYY" date may have in the CV."""
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{4})", value.strip())
    if not m:
        return []
    mm, yy = int(m.group(1)), m.group(2)
    if not 1 <= mm <= 12:
        return []
    full = _MONTHS[mm - 1]
    abbr = full[:3]
    return [f"{abbr} {yy}", f"{abbr}. {yy}", f"{full} {yy}", f"{mm}/{yy}", f"{mm:02d}/{yy}",
            f"{mm:02d}-{yy}", f"{mm}-{yy}", f"{mm:02d}.{yy}", f"T{mm}/{yy}", f"Tháng {mm}/{yy}", f"{abbr.upper()} {yy}"]


class Aligner:
    def __init__(self, text: str, stats: Counter):
        self.text = text
        self.norm, self.map = normalize_with_map(text)
        self.stats = stats

    def snap(self, value: Any, field: str) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        span = find_span(value, self.text, cv_norm=self.norm, cv_map=self.map)
        if span is None:
            self.stats[f"dropped_{field}"] += 1
            return None
        if span != value:
            self.stats[f"snapped_{field}"] += 1
        return span

    def snap_date(self, value: Any, field: str) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        if value in self.text:
            return value
        for cand in date_candidates(value):
            m = re.search(r"(?<!\w)" + re.escape(cand) + r"(?!\w)", self.text, re.IGNORECASE)
            if m:
                self.stats[f"date_respelled_{field}"] += 1
                return m.group(0)
        return self.snap(value, field)

    def snap_list(self, items: list, field: str) -> list[str]:
        out = []
        for v in items or []:
            s = self.snap(v, field)
            if s is not None and s not in out:
                out.append(s)
        return out


def align_label(text: str, label: dict, stats: Counter) -> dict:
    """Return a v3 label whose string values all occur in ``text``."""
    p = normalize_profile(copy.deepcopy(label))
    a = Aligner(text, stats)

    pi = p["personal_info"]
    for k in ("full_name", "email", "github_url"):
        pi[k] = a.snap(pi.get(k), k)
    phone = pi.get("phone")
    digits = re.sub(r"\D", "", phone or "")
    pi["phone"] = phone if digits and digits in re.sub(r"\D", "", text) else None
    p["objective"] = a.snap(p.get("objective"), "objective")

    edu = []
    for e in p["education"]:
        e["school"] = a.snap(e.get("school"), "school")
        if not e["school"]:
            continue
        e["major"] = a.snap(e.get("major"), "major")
        e["gpa"] = a.snap(e.get("gpa"), "gpa")
        edu.append(e)
    p["education"] = edu

    exp = []
    for e in p["experience"]:
        company = e.get("company")
        if isinstance(company, str):
            short = strip_location(company)
            if short != company:
                stats["company_location_stripped"] += 1
            company = short
        e["company"] = a.snap(company, "company")
        if not e["company"]:
            continue
        e["job_title"] = a.snap(e.get("job_title"), "job_title")
        for k in ("start_date", "end_date"):
            e[k] = a.snap_date(e.get(k), k)
        e["description"] = a.snap_list(e.get("description"), "bullet")
        exp.append(e)
    p["experience"] = exp

    projects = []
    for pr in p["personal_projects"]:
        pr["name"] = a.snap(pr.get("name"), "project")
        if not pr["name"]:
            continue
        for k in ("role", "github_url"):
            pr[k] = a.snap(pr.get(k), k)
        for k in ("start_date", "end_date"):
            pr[k] = a.snap_date(pr.get(k), k)
        pr["description"] = a.snap_list(pr.get("description"), "bullet")
        pr["tech_stack"] = a.snap_list(clean_skill_list(pr.get("tech_stack")), "tech")
        projects.append(pr)
    p["personal_projects"] = projects

    skills = clean_skill_list(p["skills"])
    langs = []
    for item in p["languages"]:
        name = item.get("language")
        if is_programming_language(name):
            stats["language_was_programming"] += 1
            skills.append(name)
            continue
        snapped = a.snap(name, "language")
        if snapped:
            langs.append({"language": snapped, "note": a.snap(item.get("note"), "language_note")})
    p["languages"] = langs
    p["skills"] = a.snap_list(skills, "skill")
    p["certificates"] = a.snap_list(p["certificates"], "certificate")
    p["honours"] = a.snap_list(p["honours"], "honour")
    return p
