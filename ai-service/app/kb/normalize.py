"""Pure normalisation of extracted CV profiles using the KnowledgeBase."""

from __future__ import annotations

import copy
from typing import Any

__all__ = ["normalize_profile_with_kb"]


def _normalize_skill_list(items: Any, linker: Any) -> Any:
    if not isinstance(items, list):
        return items

    expanded: list[Any] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            links = linker.link_many([item])
            if links and all(
                (getattr(l, "skill_id", None) if hasattr(l, "skill_id") else l.get("skill_id")) is not None
                and (getattr(l, "name", None) if hasattr(l, "name") else l.get("name")) is not None
                for l in links
            ) and not all(
                # Soft skills stay as the CV wrote them ("Làm việc nhóm", not ESCO's "work in teams");
                # their link is still available with include=kg.
                (getattr(l, "category", None) if hasattr(l, "category") else l.get("category")) == "Soft Skill"
                for l in links
            ):
                for l in links:
                    c_name = getattr(l, "name", None) if hasattr(l, "name") else l.get("name")
                    expanded.append(c_name)
            else:
                expanded.append(item)
        else:
            expanded.append(item)

    seen: set[str] = set()
    deduped: list[Any] = []
    for it in expanded:
        if isinstance(it, str):
            k = it.casefold()
            if k not in seen:
                seen.add(k)
                deduped.append(it)
        else:
            deduped.append(it)
    return deduped


def normalize_profile_with_kb(profile: dict[str, Any], kb: Any) -> dict[str, Any]:
    """Replace linked skills, project tech_stack, and school names with KB canonical names.

    Pure function: does not mutate profile, does not log, produces no I/O.
    """
    if not isinstance(profile, dict):
        return profile

    result = copy.deepcopy(profile)
    if kb is None:
        return result

    linker = getattr(kb, "linker", None)
    link_school = getattr(kb, "link_school", None)
    if linker is None or not hasattr(linker, "link_many") or not callable(linker.link_many):
        return result
    if link_school is None or not callable(link_school):
        return result

    if "skills" in result and isinstance(result["skills"], list):
        result["skills"] = _normalize_skill_list(result["skills"], linker)

    if "personal_projects" in result and isinstance(result["personal_projects"], list):
        for proj in result["personal_projects"]:
            if isinstance(proj, dict) and "tech_stack" in proj and isinstance(proj["tech_stack"], list):
                proj["tech_stack"] = _normalize_skill_list(proj["tech_stack"], linker)

    if "education" in result and isinstance(result["education"], list):
        for edu in result["education"]:
            if isinstance(edu, dict) and "school" in edu and isinstance(edu["school"], str):
                school_val = edu["school"].strip()
                if school_val:
                    res = link_school(school_val)
                    if isinstance(res, (tuple, list)) and len(res) >= 2 and res[1]:
                        edu["school"] = res[1]

    return result
