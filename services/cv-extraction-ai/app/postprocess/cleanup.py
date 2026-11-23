"""Output completion post-processing cleanup (feature 012).

Pure functions to clean:
1. FR-2a: Drop experience items whose company matches a personal project name.
2. FR-2b: Drop experience items whose company is only an address.
3. FR-3: Drop junk skills and tech_stack items (bare numbers, punctuation, or > 8 words).
"""

from __future__ import annotations

import re
from typing import Any

from app.postprocess.text_match import normalize

__all__ = [
    "cleanup_profile",
    "is_address_only_company",
    "is_junk_skill",
]

_PROVINCES: list[str] = [
    "an giang", "ba ria vung tau", "ba ria", "vung tau", "bac giang", "bac kan",
    "bac lieu", "bac ninh", "ben tre", "binh dinh", "binh duong", "binh phuoc",
    "binh thuan", "ca mau", "can tho", "cao bang", "da nang", "danang", "dak lak",
    "dac lac", "dak nong", "dac nong", "dien bien", "dong nai", "dong thap",
    "gia lai", "ha giang", "ha nam", "ha noi", "hanoi", "ha tinh", "hai duong",
    "hai phong", "haiphong", "hau giang", "hoa binh", "hung yen", "khanh hoa",
    "kien giang", "kon tum", "lai chau", "lam dong", "lang son", "lao cai",
    "long an", "nam dinh", "nghe an", "ninh binh", "ninh thuan", "phu tho",
    "phu yen", "quang binh", "quang nam", "quang ngai", "quang ninh", "quang tri",
    "soc trang", "son la", "tay ninh", "thai binh", "thai nguyen", "thanh hoa",
    "thua thien hue", "hue", "tien giang", "ho chi minh", "sai gon", "saigon",
    "hcm", "tphcm", "tra vinh", "tuyen quang", "vinh long", "vinh phuc", "yen bai",
]

_ADMIN_PHRASES: list[str] = [
    "phuong", "quan", "huyen", "xa", "thi tran", "thanh pho", "tp", "tinh",
    "district", "ward", "city", "province", "street", "duong",
]

_COUNTRIES: list[str] = ["viet nam", "vietnam"]

_LOCALITY_TOKENS: frozenset[str] = frozenset(
    token
    for phrase in (_PROVINCES + _ADMIN_PHRASES + _COUNTRIES)
    for token in phrase.split()
)

_ADMIN_PATTERN: re.Pattern = re.compile(
    r"\b(thi tran|thanh pho|phuong|quan|huyen|xa|tp|tinh|district|ward|city|province|street|duong)\b",
    re.IGNORECASE,
)


def _inc(stats: Any, name: str, n: int = 1) -> None:
    if stats is None or n == 0:
        return
    setattr(stats, name, getattr(stats, name, 0) + n)


_ORG_PATTERN = re.compile(
    r"\b(cong ty|cty|company|corp|corporation|jsc|ltd|llc|inc|co|group|tap doan|ngan hang|bank|truong|"
    r"university|hoc vien|benh vien|hospital|clinic|software|technology|technologies|tech|solutions?|"
    r"studio|agency|bo|so|vien|center|centre|trung tam|shop|store|restaurant|hotel|factory|nha may)\b"
)


def is_address_only_company(company: Any) -> bool:
    """Return True if company is purely a locality address."""
    if not isinstance(company, str) or not company.strip():
        return False

    norm = normalize(company)
    if not norm:
        return False

    # Condition 1: after stripping punctuation, every token belongs to the locality dictionary
    tokens = re.findall(r"[a-z0-9]+", norm)
    if tokens and any(not t.isdigit() for t in tokens) and all(t in _LOCALITY_TOKENS or t.isdigit() for t in tokens):
        return True

    # Condition 2: "Ward, District, Province" — >= 3 comma parts, last part a locality,
    # and no organisation word anywhere ("Bệnh viện Đa khoa Tỉnh Bình Dương" is kept).
    parts = [p.strip() for p in norm.split(",") if p.strip()]
    if len(parts) >= 3 and not _ORG_PATTERN.search(norm):
        last = re.findall(r"[a-z0-9]+", parts[-1])
        if last and all(t in _LOCALITY_TOKENS or t.isdigit() for t in last):
            return True

    return False


def is_junk_skill(skill: Any) -> bool:
    """Return True if skill item is junk (digits/punct only or > 8 words)."""
    if not isinstance(skill, str):
        if skill is None:
            return True
        skill = str(skill)
    s = skill.strip()
    if not s:
        return True

    # Drop if only digits, punctuation, and whitespace (no letters)
    if not any(c.isalpha() for c in s):
        return True

    # Drop if > 8 words (sentence)
    if len(s.split()) > 8:
        return True

    return False


def clean_junk_skills(items: Any, stats: Any = None) -> list[str]:
    """Filter out junk skills from a skill list and bump stats counter."""
    if items is None:
        return []
    if not isinstance(items, list):
        return items

    kept: list[str] = []
    removed = 0
    for item in items:
        if is_junk_skill(item):
            removed += 1
        else:
            kept.append(item)

    _inc(stats, "skills_removed_junk", removed)
    return kept


def cleanup_profile(profile: dict[str, Any], stats: Any = None) -> dict[str, Any]:
    """Clean extracted profile (FR-2a, FR-2b, FR-3). Pure function returning profile."""
    if not isinstance(profile, dict):
        return profile

    # FR-2a: Collect project names in the same profile
    project_names: set[str] = set()
    raw_projects = profile.get("personal_projects")
    if isinstance(raw_projects, list):
        for proj in raw_projects:
            if isinstance(proj, dict):
                pname = proj.get("name")
                if pname and isinstance(pname, str):
                    p_norm = normalize(pname)
                    if p_norm:
                        project_names.add(p_norm)

    # Filter experience (FR-2a & FR-2b)
    raw_exp = profile.get("experience")
    if isinstance(raw_exp, list):
        kept_exp: list[dict[str, Any]] = []
        for exp in raw_exp:
            if not isinstance(exp, dict):
                kept_exp.append(exp)
                continue

            company = exp.get("company")
            comp_norm = normalize(company) if isinstance(company, str) else ""

            # FR-2a: company matches a project name
            if comp_norm and comp_norm in project_names:
                _inc(stats, "experience_removed_project")
                continue

            # FR-2b: company is only an address
            if isinstance(company, str) and is_address_only_company(company):
                _inc(stats, "experience_removed_address")
                continue

            kept_exp.append(exp)

        profile["experience"] = kept_exp

    # FR-3: Filter skills
    if "skills" in profile and isinstance(profile["skills"], list):
        profile["skills"] = clean_junk_skills(profile["skills"], stats)

    # FR-3: Filter personal_projects[].tech_stack
    if isinstance(raw_projects, list):
        for proj in raw_projects:
            if isinstance(proj, dict) and "tech_stack" in proj and isinstance(proj["tech_stack"], list):
                proj["tech_stack"] = clean_junk_skills(proj["tech_stack"], stats)

    return profile
