"""Grounding and validation of extracted CV entities against source CV text.

Tier-3 post-processing pure function:
- Removes ungrounded entities (companies, schools, projects, contacts, certificates, etc.)
- Snaps near-miss entity names to exact CV text (fuzzy >= 85)
- Filters invalid experience types (students, non-teaching roles at universities)
- Merges ungrounded experience bullets into corresponding projects
- Validates languages against aliases and CV context
- Deduplicates identical items across sections
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from app.postprocess.text_match import (
    contains,
    digits,
    find_span,
    normalize,
    normalize_with_map,
)

__all__ = ["ground_profile"]

_SCHOOL_RE = re.compile(
    r"\b(dai hoc|university|truong|hoc vien|college|academy|institute|cao dang|thpt)\b"
)

_TEACHING_OR_STAFF_RE = re.compile(
    r"(giang vien|lecturer|teacher|giao vien|tro giang|teaching assistant|nghien cuu vien|research|staff|nhan vien|can bo)"
)

_STUDENT_TITLE_RE = re.compile(r"^(sinh vien|student|hoc vien)$")

_LANGUAGE_GROUPS: list[dict[str, Any]] = [
    {
        "name": "english",
        "aliases": ("english", "tieng anh", "anh"),
    },
    {
        "name": "japanese",
        "aliases": ("japanese", "tieng nhat", "nhat"),
    },
    {
        "name": "korean",
        "aliases": ("korean", "tieng han", "han"),
    },
    {
        "name": "chinese",
        "aliases": ("chinese", "tieng trung", "trung"),
    },
    {
        "name": "french",
        "aliases": ("french", "tieng phap", "phap"),
    },
    {
        "name": "german",
        "aliases": ("german", "tieng duc", "duc"),
    },
    {
        "name": "vietnamese",
        "aliases": ("vietnamese", "tieng viet", "viet"),
    },
]

_SINGLE_WORD_LANG_ALIASES = frozenset({"anh", "nhat", "han", "trung", "phap", "duc", "viet"})
_LANG_CONTEXT_RE = re.compile(r"\b(ngoai ngu|language|tieng)\b")


def _inc(stats: Any, name: str, n: int = 1) -> None:
    """Increment counter attribute on stats object if provided."""
    if stats is None or n == 0:
        return
    setattr(stats, name, getattr(stats, name, 0) + n)


def _is_language_grounded(item: dict[str, Any], cv_norm: str) -> bool:
    """Check if a language item is grounded in normalized CV text."""
    if not isinstance(item, dict):
        return False

    lang = item.get("language")
    note = item.get("note")

    # 1. Direct contains check on language or note
    if lang and contains(cv_norm, str(lang)):
        return True
    if note and contains(cv_norm, str(note)):
        return True

    # 2. Check alias group
    lang_norm = normalize(str(lang)) if lang else ""
    if not lang_norm:
        return False

    matched_group = None
    for grp in _LANGUAGE_GROUPS:
        for alias in grp["aliases"]:
            if alias in _SINGLE_WORD_LANG_ALIASES:
                if re.search(rf"\b{re.escape(alias)}\b", lang_norm):
                    matched_group = grp
                    break
            else:
                if alias in lang_norm:
                    matched_group = grp
                    break
        if matched_group:
            break

    if not matched_group:
        return False

    has_lang_context = bool(_LANG_CONTEXT_RE.search(cv_norm))

    for alias in matched_group["aliases"]:
        if alias in _SINGLE_WORD_LANG_ALIASES:
            if has_lang_context and re.search(rf"\b{re.escape(alias)}\b", cv_norm):
                return True
        else:
            if re.search(rf"\b{re.escape(alias)}\b", cv_norm):
                return True

    return False


_TITLE_WINDOW_BEFORE = 200
_TITLE_WINDOW_AFTER = 300


def _near(cv_norm: str, company: str, title: str) -> bool:
    """True if ``title`` occurs within a window around any occurrence of ``company``."""
    comp = normalize(company)
    if not comp:
        return contains(cv_norm, title)
    pos = cv_norm.find(comp)
    if pos < 0:  # company was snapped by fuzzy match: fall back to whole-CV containment
        return contains(cv_norm, title)
    while pos >= 0:
        window = cv_norm[max(0, pos - _TITLE_WINDOW_BEFORE): pos + len(comp) + _TITLE_WINDOW_AFTER]
        if contains(window, title):
            return True
        pos = cv_norm.find(comp, pos + 1)
    return False


def _contains_compact(cv_compact: str, value: str) -> bool:
    """Containment ignoring all whitespace (accent/case-insensitive)."""
    v = normalize(value).replace(" ", "")
    return bool(v) and v in cv_compact


def ground_profile(
    profile: dict[str, Any],
    cv_text: str,
    stats: Any = None,
) -> dict[str, Any]:
    """Ground and clean profile against cv_text.

    Pure function: does not mutate input profile.
    If cv_text is empty or blank, returns a deep copy of profile untouched.
    """
    if not isinstance(profile, dict):
        return {}

    if not cv_text or not isinstance(cv_text, str) or not cv_text.strip():
        return copy.deepcopy(profile)

    cv_norm, cv_map = normalize_with_map(cv_text)
    if not cv_norm:
        return copy.deepcopy(profile)

    res = copy.deepcopy(profile)
    cv_digs = digits(cv_text)
    # Whitespace-free view: PDF text often breaks URLs/emails across lines.
    cv_compact = cv_norm.replace(" ", "")

    # -------------------------------------------------------------
    # 1. personal_info grounding
    # -------------------------------------------------------------
    personal_info = res.get("personal_info")
    if isinstance(personal_info, dict):
        # email
        email = personal_info.get("email")
        if email is not None:
            if not _contains_compact(cv_compact, str(email)):
                personal_info["email"] = None
                _inc(stats, "contacts_nulled")

        # github_url
        github_url = personal_info.get("github_url")
        if github_url is not None:
            gh_clean = str(github_url).strip()
            gh_clean = re.sub(r"^https?://", "", gh_clean, flags=re.IGNORECASE)
            gh_clean = re.sub(r"^www\.", "", gh_clean, flags=re.IGNORECASE)
            gh_clean = gh_clean.rstrip("/")
            if not gh_clean or not _contains_compact(cv_compact, gh_clean):
                personal_info["github_url"] = None
                _inc(stats, "contacts_nulled")

        # phone
        phone = personal_info.get("phone")
        if phone is not None:
            p_digs = digits(str(phone))
            matched = False
            if len(p_digs) >= 8:
                if p_digs in cv_digs:
                    matched = True
                elif p_digs.startswith("84") and ("0" + p_digs[2:]) in cv_digs:
                    matched = True
                elif p_digs.startswith("0") and ("84" + p_digs[1:]) in cv_digs:
                    matched = True
            if not matched:
                personal_info["phone"] = None
                _inc(stats, "contacts_nulled")

        # full_name
        full_name = personal_info.get("full_name")
        if full_name is not None:
            span = find_span(str(full_name), cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                personal_info["full_name"] = None
                _inc(stats, "contacts_nulled")
            else:
                personal_info["full_name"] = span

    # -------------------------------------------------------------
    # 2. experience grounding & type check
    # -------------------------------------------------------------
    raw_exp = res.get("experience")
    kept_experiences: list[dict[str, Any]] = []
    ungrounded_experiences: list[dict[str, Any]] = []

    if isinstance(raw_exp, list):
        for exp in raw_exp:
            if not isinstance(exp, dict):
                continue

            company = exp.get("company")
            if not company or not isinstance(company, str) or not company.strip():
                _inc(stats, "experience_removed_ungrounded")
                ungrounded_experiences.append(exp)
                continue

            span = find_span(company, cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                _inc(stats, "experience_removed_ungrounded")
                ungrounded_experiences.append(exp)
                continue

            if span != company:
                _inc(stats, "names_snapped")
            exp["company"] = span

            # job_title must come from the CV; a CV may give no title at all (real CVs do),
            # so an absent or ungrounded title is nulled instead of dropping the experience.
            # The title must appear near the company (same experience block), not just anywhere:
            # "backend developer" in the objective is not this job's title.
            job_title = exp.get("job_title")
            if job_title is not None and (
                not isinstance(job_title, str) or not _near(cv_norm, exp["company"], job_title)
            ):
                exp["job_title"] = None
                job_title = None
                _inc(stats, "titles_nulled")
            title_norm = normalize(job_title) if job_title else ""

            # Type check: student "jobs" are not experience
            if title_norm and _STUDENT_TITLE_RE.fullmatch(title_norm):
                _inc(stats, "experience_removed_type")
                continue

            comp_norm = normalize(exp["company"])
            if _SCHOOL_RE.search(comp_norm) and not _TEACHING_OR_STAFF_RE.search(title_norm):
                _inc(stats, "experience_removed_type")
                continue

            kept_experiences.append(exp)

        res["experience"] = kept_experiences

    # -------------------------------------------------------------
    # 4. education & personal_projects grounding (run before merge)
    # -------------------------------------------------------------
    raw_edu = res.get("education")
    kept_education: list[dict[str, Any]] = []
    if isinstance(raw_edu, list):
        for edu in raw_edu:
            if not isinstance(edu, dict):
                continue
            school = edu.get("school")
            if not school or not isinstance(school, str) or not school.strip():
                _inc(stats, "education_removed")
                continue
            span = find_span(school, cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                _inc(stats, "education_removed")
                continue
            if span != school:
                _inc(stats, "names_snapped")
            edu["school"] = span
            kept_education.append(edu)
        res["education"] = kept_education

    raw_proj = res.get("personal_projects")
    kept_projects: list[dict[str, Any]] = []
    if isinstance(raw_proj, list):
        for proj in raw_proj:
            if not isinstance(proj, dict):
                continue
            name = proj.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                _inc(stats, "projects_removed")
                continue
            span = find_span(name, cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                _inc(stats, "projects_removed")
                continue
            if span != name:
                _inc(stats, "names_snapped")
            proj["name"] = span
            kept_projects.append(proj)
        res["personal_projects"] = kept_projects

    # -------------------------------------------------------------
    # 3. merge ungrounded experiences into projects
    # -------------------------------------------------------------
    for u_exp in ungrounded_experiences:
        company = u_exp.get("company")
        exp_desc = u_exp.get("description")
        if not company or not exp_desc:
            continue
        company_norm = normalize(str(company))
        if not company_norm:
            continue

        target_project = None
        for proj in kept_projects:
            pname = proj.get("name")
            if not pname:
                continue
            pname_norm = normalize(str(pname))
            if len(pname_norm) >= 3 and pname_norm in company_norm:
                target_project = proj
                break

        if target_project is None:
            continue

        proj_desc = target_project.get("description")
        if proj_desc is None:
            proj_desc = []
            target_project["description"] = proj_desc
        elif not isinstance(proj_desc, list):
            proj_desc = [str(proj_desc)]
            target_project["description"] = proj_desc

        bullets_to_add = exp_desc if isinstance(exp_desc, list) else [str(exp_desc)]
        existing_norm = {normalize(str(b)) for b in proj_desc if b and normalize(str(b))}
        added_count = 0
        for b in bullets_to_add:
            if not b or not isinstance(b, str) or not b.strip():
                continue
            b_norm = normalize(b)
            if b_norm and b_norm not in existing_norm:
                proj_desc.append(b)
                existing_norm.add(b_norm)
                added_count += 1

        _inc(stats, "bullets_merged", added_count)

    # -------------------------------------------------------------
    # 5. objective, certificates, honours, languages
    # -------------------------------------------------------------
    # objective
    obj = res.get("objective")
    if obj is not None:
        if isinstance(obj, str) and obj.strip():
            span = find_span(obj, cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                res["objective"] = None
                _inc(stats, "items_removed_ungrounded")
            else:
                res["objective"] = span
        else:
            res["objective"] = None

    # skills: keep only items found in the CV (same fuzzy containment as other lists)
    raw_skills = res.get("skills")
    if isinstance(raw_skills, list):
        cv_compact = cv_norm.replace(" ", "")
        kept_skills = [
            s for s in raw_skills
            if isinstance(s, str) and s.strip()
            and (contains(cv_norm, s) or _contains_compact(cv_compact, s))
        ]
        _inc(stats, "items_removed_ungrounded", len(raw_skills) - len(kept_skills))
        res["skills"] = kept_skills

    # certificates
    raw_certs = res.get("certificates")
    kept_certs: list[str] = []
    if isinstance(raw_certs, list):
        for cert in raw_certs:
            if not cert or not isinstance(cert, str) or not cert.strip():
                _inc(stats, "items_removed_ungrounded")
                continue
            span = find_span(cert, cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                _inc(stats, "items_removed_ungrounded")
            else:
                kept_certs.append(cert)
        res["certificates"] = kept_certs

    # honours
    raw_honours = res.get("honours")
    kept_honours: list[str] = []
    if isinstance(raw_honours, list):
        for honour in raw_honours:
            if not honour or not isinstance(honour, str) or not honour.strip():
                _inc(stats, "items_removed_ungrounded")
                continue
            span = find_span(honour, cv_text, cv_norm=cv_norm, cv_map=cv_map)
            if span is None:
                _inc(stats, "items_removed_ungrounded")
            else:
                kept_honours.append(honour)
        res["honours"] = kept_honours

    # languages
    raw_langs = res.get("languages")
    kept_langs: list[dict[str, Any]] = []
    if isinstance(raw_langs, list):
        for lang_item in raw_langs:
            if _is_language_grounded(lang_item, cv_norm):
                kept_langs.append(lang_item)
            else:
                _inc(stats, "items_removed_ungrounded")
        res["languages"] = kept_langs

    # -------------------------------------------------------------
    # 6. Deduplicate exact duplicate items in every section list
    # -------------------------------------------------------------
    for sec_name in (
        "education",
        "experience",
        "personal_projects",
        "skills",
        "certificates",
        "honours",
        "languages",
    ):
        sec_list = res.get(sec_name)
        if not isinstance(sec_list, list):
            continue
        seen: set[str] = set()
        deduped: list[Any] = []
        for item in sec_list:
            key = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if key in seen:
                _inc(stats, "duplicates_removed")
            else:
                seen.add(key)
                deduped.append(item)
        res[sec_name] = deduped

    return res
