"""Input normalization for candidate CVs and job descriptions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DICTIONARY_PATH = ROOT / "data" / "skills_dictionary.json"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_text(item) for item in re.split(r"[,;\n]", value) if _text(item)]
    if isinstance(value, (list, tuple, set)):
        return [_text(item) for item in value if _text(item)]
    return []


def load_skill_dictionary(path: Path = DICTIONARY_PATH) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return {_text(key): _text(value) for key, value in raw.items()}


def _normalize_skills(value: Any, dictionary: dict[str, str]) -> list[str]:
    normalized = []
    for item in _items(value):
        normalized.append(dictionary.get(item, item))
    return list(dict.fromkeys(normalized))


def normalize_candidate(candidate: dict[str, Any], dictionary: dict[str, str] | None = None) -> dict[str, Any]:
    dictionary = dictionary or load_skill_dictionary()
    education = candidate.get("education")
    if isinstance(education, dict):
        education_level = education.get("degree") or education.get("level")
        education_major = _text(education.get("major"))
    else:
        education_level = education
        education_major = ""
    return {
        "name": _text(candidate.get("name")),
        "skills": _normalize_skills(candidate.get("skills"), dictionary),
        "experience_years": max(0.0, float(candidate.get("experience_years") or 0)),
        "job_titles": _items(candidate.get("job_titles")),
        "education": _text(education_level),
        "education_major": education_major,
        "certificates": _items(candidate.get("certificates")),
        "raw_context": _text(candidate.get("raw_context") or candidate.get("summary")),
    }


def normalize_jd(jd: dict[str, Any], dictionary: dict[str, str] | None = None) -> dict[str, Any]:
    dictionary = dictionary or load_skill_dictionary()
    education = jd.get("education") or jd.get("required_education") or jd.get("education_requirement")
    return {
        "title": _text(jd.get("title")),
        "required_skills": _normalize_skills(jd.get("required_skills") or jd.get("skills"), dictionary),
        "min_experience_years": max(0.0, float(jd.get("min_experience_years") or 0)),
        "required_title": _text(jd.get("required_title") or jd.get("title")),
        "education": _education_requirement(education),
        "context": _text(jd.get("context") or jd.get("description")),
    }


def _education_requirement(value: Any) -> str:
    text = _text(value)
    levels = ("tiến sĩ", "phd", "thạc sĩ", "master", "cử nhân", "bachelor", "đại học", "cao đẳng", "associate")
    return next((level for level in levels if level in text), text)
