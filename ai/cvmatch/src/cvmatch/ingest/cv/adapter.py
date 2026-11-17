"""Doi ten truong tu schema THAT cua CV JSON sang schema noi bo (thiet ke 04, cau hoi Q-1).

Ten truong trong thiet ke la gia dinh. Khi co schema that chi can sua cac bang anh xa duoi day,
logic A1-A11 giu nguyen. Ten khong co trong bang duoc giu nguyen.
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


def adapt_cv(raw: dict) -> dict:
    """JSON ngoai -> JSON theo ten truong noi bo. Khong doi gia tri."""
    if not isinstance(raw, dict):
        return raw
    cv = _rename(raw, TOP_LEVEL)
    for key, mapping in (("experiences", EXPERIENCE), ("projects", PROJECT), ("education", EDUCATION)):
        if isinstance(cv.get(key), list):
            cv[key] = [_rename(x, mapping) for x in cv[key]]
    return cv
