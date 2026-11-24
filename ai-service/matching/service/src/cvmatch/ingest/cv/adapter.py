"""Doi ten truong tu schema THAT cua CV JSON sang schema noi bo (thiet ke 04, cau hoi Q-1).

Ten truong trong thiet ke la gia dinh. Khi co schema that chi can sua cac bang anh xa duoi day,
logic A1-A11 giu nguyen. Ten khong co trong bang duoc giu nguyen.

Schema that cua Module 1 (`services/cv-extraction-ai`, `app/postprocess/schema.py`, I03 cua plan tich hop):
`personal_info{full_name, email, phone, github_url}`, `objective`, `experience[{company, job_title, start_date,
end_date, description[]}]`, `personal_projects[{name, role, team_size, start_date, end_date, github_url,
description[], tech_stack[]}]`, `education[{school, major, start_year, end_year, gpa}]`, `skills[]`,
`certificates[]`, `honours[]`, `languages[{language, note}]`; voi `?include=kg` them `skills_normalized`,
`implied_skills`, `skills_detected`, `related_skills`, `flags` (KG_FIELDS).

- `personal_info.*` duoc keo len cap goc (gia tri cap goc co san thang): can `email` / `phone` cho A2.
- Truong KG bi bo: la suy dien cua KG Module 1, khong phai noi dung CV (ky nang suy ra khong duoc tinh nhu co that).
  Luu y `content_hash` (A2) tinh tren JSON DAU VAO: ben gui nen bo truong KG truoc khi gui de KG doi khong sinh
  version CV moi.
- `experience[].end_date = null` (co `start_date`) -> `is_current = true` (quy uoc cua Module 1).
- Backend (I05) gui email TAI KHOAN trong `personal_info.email` va them `location` neu co.
"""

from __future__ import annotations

from typing import Any

# truong cap goc: ten ngoai -> ten noi bo
TOP_LEVEL = {
    "name": "full_name",
    "fullname": "full_name",
    "ho_ten": "full_name",
    "mail": "email",
    "phone_number": "phone",
    "sdt": "phone",
    "dob": "birth_date",
    "date_of_birth": "birth_date",
    "address": "address",
    "objective": "summary",
    "about": "summary",
    "profile": "summary",
    "experience": "experiences",
    "work_experience": "experiences",
    "work_experiences": "experiences",
    "employment": "experiences",
    "project": "projects",
    "personal_projects": "projects",
    "honors": "honours",
    "awards": "honours",
    "educations": "education",
    "certifications": "certificates",
    "certificate": "certificates",
    "skill": "skills",
    "technical_skills": "skills",
}

EXPERIENCE = {
    "position": "title",
    "job_title": "title",
    "role": "title",
    "company_name": "company",
    "start_date": "start",
    "from": "start",
    "end_date": "end",
    "to": "end",
    "current": "is_current",
    "responsibilities": "description",
    "achievements": "description",
    "tech_stack": "technologies",
    "tools": "technologies",
    "type": "kind",
}

PROJECT = {
    "project_name": "name",
    "title": "name",
    "start_date": "start",
    "end_date": "end",
    "tech_stack": "technologies",
    "tools": "technologies",
    "team": "team_size",
    "type": "kind",
}

EDUCATION = {
    "university": "school",
    "school_name": "school",
    "field_of_study": "major",
    "field": "major",
    "degree": "level",
    "start_date": "start",
    "end_date": "end",
    "graduation": "end",
    "start_year": "start",
    "end_year": "end",
}


def _rename(obj: Any, mapping: dict[str, str]) -> Any:
    if not isinstance(obj, dict):
        return obj
    out: dict[str, Any] = {}
    for k, v in obj.items():
        key = mapping.get(k, k)
        if key in out and out[key] not in (None, "", []):  # khong de truong rong de len
            continue
        out[key] = v
    return out


# Truong do KG cua Module 1 them (`?include=kg`): khong dua vao matching
KG_FIELDS = ("skills_normalized", "implied_skills", "skills_detected", "related_skills", "flags")
PERSONAL_INFO = {"name": "full_name", "phone_number": "phone", "mail": "email", "github": "github_url"}


def _lift_personal_info(raw: dict) -> dict:
    info = raw.get("personal_info")
    if not isinstance(info, dict):
        return raw
    out = {k: v for k, v in raw.items() if k != "personal_info"}
    for k, v in _rename(info, PERSONAL_INFO).items():
        if out.get(k) in (None, "", []):
            out[k] = v
    return out


def adapt_cv(raw: dict) -> dict:
    """JSON ngoai -> JSON theo ten truong noi bo. Khong doi gia tri."""
    if not isinstance(raw, dict):
        return raw
    raw = {k: v for k, v in _lift_personal_info(raw).items() if k not in KG_FIELDS}
    cv = _rename(raw, TOP_LEVEL)
    for key, mapping in (("experiences", EXPERIENCE), ("projects", PROJECT), ("education", EDUCATION)):
        if isinstance(cv.get(key), list):
            cv[key] = [_rename(x, mapping) for x in cv[key]]
    if isinstance(raw.get("experience"), list) and isinstance(cv.get("experiences"), list):
        for src, item in zip(raw["experience"], cv["experiences"]):
            if _module1_current(src, item):
                item["is_current"] = True
    return cv


def _module1_current(src: Any, item: Any) -> bool:
    """Module 1: `end_date = null` nghia la DANG LAM (prompt: "end_date = null neu dang lam"). Chi ap dung khi
    muc co `start_date` va khai bao `end_date` ro rang, khong co `is_current`."""
    return (isinstance(src, dict) and isinstance(item, dict) and "end_date" in src and src["end_date"] in (None, "")
            and bool(src.get("start_date")) and "is_current" not in src and "current" not in src)
