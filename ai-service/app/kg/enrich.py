"""Knowledge Graph enrichment of extracted CV profiles."""

from __future__ import annotations

import collections
import copy
from typing import Any

__all__ = ["enrich"]


def _stat_val(stats: dict[str, Any], key: str) -> int:
    val = stats.get(key, 0)
    if val is None:
        return 0
    try:
        count = int(val)
        return count if count > 0 else 0
    except (ValueError, TypeError):
        return 0


def enrich(
    profile: dict[str, Any],
    kb: Any,
    pp_stats: Any = None,
) -> dict[str, Any]:
    """Enrich an extracted CV profile with canonical entities, implied skills, and flags.

    Pure function: never mutates ``profile``, produces no I/O and no logs.
    """
    enriched = copy.deepcopy(profile) if isinstance(profile, dict) else {}

    # -------------------------------------------------------------------------
    # 1. Normalised skills
    # -------------------------------------------------------------------------
    raw_skills = enriched.get("skills") or []
    if not isinstance(raw_skills, (list, tuple)):
        raw_skills = [raw_skills]

    linker = getattr(kb, "linker", None)
    if linker is not None and callable(getattr(linker, "link_many", None)):
        links = linker.link_many(raw_skills)
    else:
        links = []

    skills_normalized: list[dict[str, Any]] = []
    for link in links:
        if isinstance(link, dict):
            raw = link.get("raw")
            sid = link.get("skill_id", link.get("id"))
            name = link.get("name")
            category = link.get("category")
            method = link.get("method")
        else:
            raw = getattr(link, "raw", None)
            sid = getattr(link, "skill_id", getattr(link, "id", None))
            name = getattr(link, "name", None)
            category = getattr(link, "category", None)
            method = getattr(link, "method", None)

        skills_normalized.append({
            "raw": raw,
            "id": sid,
            "name": name,
            "category": category,
            "method": method,
        })

    enriched["skills_normalized"] = skills_normalized

    # -------------------------------------------------------------------------
    # 2. Implied skills (BFS over REQUIRES / PART_OF relations)
    # -------------------------------------------------------------------------
    linked_ids: list[int] = []
    for item in skills_normalized:
        sid = item.get("id")
        if sid is not None and sid not in linked_ids:
            linked_ids.append(sid)

    visited: set[int] = set(linked_ids)
    queue: collections.deque[tuple[int, int]] = collections.deque(
        (sid, 0) for sid in linked_ids
    )

    edges_map: dict[int, list[tuple[str, int]]] = getattr(kb, "edges", {}) or {}
    skills_map: dict[int, Any] = getattr(kb, "skills", {}) or {}

    discovered: list[dict[str, Any]] = []

    while queue:
        curr_id, depth = queue.popleft()
        for edge in edges_map.get(curr_id, []):
            if not (isinstance(edge, (tuple, list)) and len(edge) >= 2):
                continue
            rel, dst_id = edge[0], edge[1]
            if rel not in ("REQUIRES", "PART_OF"):
                continue
            if dst_id not in visited:
                visited.add(dst_id)
                if dst_id not in skills_map:
                    continue

                curr_skill = skills_map.get(curr_id)
                if isinstance(curr_skill, dict):
                    from_name = curr_skill.get("name", str(curr_id))
                elif isinstance(curr_skill, (tuple, list)) and len(curr_skill) >= 1:
                    from_name = curr_skill[0]
                else:
                    from_name = str(curr_id)

                dst_skill = skills_map[dst_id]
                if isinstance(dst_skill, dict):
                    dst_name = dst_skill.get("name")
                    dst_cat = dst_skill.get("category")
                elif isinstance(dst_skill, (tuple, list)):
                    dst_name = dst_skill[0] if len(dst_skill) >= 1 else None
                    dst_cat = dst_skill[1] if len(dst_skill) >= 2 else None
                else:
                    dst_name = str(dst_skill)
                    dst_cat = None

                next_depth = depth + 1
                via = [{"from": from_name, "rel": rel}]
                discovered.append({
                    "id": dst_id,
                    "name": dst_name,
                    "category": dst_cat,
                    "via": via,
                    "_depth": next_depth,
                })
                queue.append((dst_id, next_depth))

    discovered.sort(key=lambda x: (x["_depth"], (x["name"] or "").casefold()))
    enriched["implied_skills"] = [
        {
            "id": x["id"],
            "name": x["name"],
            "category": x["category"],
            "via": x["via"],
        }
        for x in discovered
    ]

    # -------------------------------------------------------------------------
    # 3. Normalised education school names
    # -------------------------------------------------------------------------
    link_school_fn = getattr(kb, "link_school", None)
    if "education" in enriched and isinstance(enriched["education"], list):
        for item in enriched["education"]:
            if isinstance(item, dict):
                raw_school = item.get("school")
                school_normalized = None
                if raw_school and callable(link_school_fn):
                    res = link_school_fn(raw_school)
                    if isinstance(res, (tuple, list)) and len(res) >= 2:
                        school_normalized = {"id": res[0], "name": res[1]}
                    elif isinstance(res, dict):
                        school_normalized = {
                            "id": res.get("id"),
                            "name": res.get("name"),
                        }
                item["school_normalized"] = school_normalized

    # -------------------------------------------------------------------------
    # 4. Advisory flags
    # -------------------------------------------------------------------------
    if pp_stats is None:
        stats: dict[str, Any] = {}
    elif hasattr(pp_stats, "as_dict") and callable(pp_stats.as_dict):
        stats = pp_stats.as_dict()
    elif isinstance(pp_stats, dict):
        stats = pp_stats
    else:
        stats = {}

    flags: list[dict[str, Any]] = []

    # 1) UNGROUNDED_REMOVED
    ungrounded_count = (
        _stat_val(stats, "items_removed_ungrounded")
        + _stat_val(stats, "education_removed")
        + _stat_val(stats, "projects_removed")
    )
    if ungrounded_count > 0:
        flags.append({
            "code": "UNGROUNDED_REMOVED",
            "count": ungrounded_count,
            "field": None,
        })

    # 2) CONTACT_NULLED
    contacts_nulled = _stat_val(stats, "contacts_nulled")
    if contacts_nulled > 0:
        flags.append({
            "code": "CONTACT_NULLED",
            "count": contacts_nulled,
            "field": None,
        })

    # 3) EXPERIENCE_REMOVED
    experience_removed = (
        _stat_val(stats, "experience_removed_ungrounded")
        + _stat_val(stats, "experience_removed_type")
    )
    if experience_removed > 0:
        flags.append({
            "code": "EXPERIENCE_REMOVED",
            "count": experience_removed,
            "field": None,
        })

    # 4) SKILLS_UNLINKED
    unlinked_skills_count = sum(
        1
        for s in skills_normalized
        if s.get("id") is None or s.get("method") == "unlinked"
    )
    if unlinked_skills_count > 0:
        flags.append({
            "code": "SKILLS_UNLINKED",
            "count": unlinked_skills_count,
            "field": "skills",
        })

    # 5) MISSING_CONTACT
    personal_info = enriched.get("personal_info")
    if isinstance(personal_info, dict):
        email = personal_info.get("email")
        phone = personal_info.get("phone")
    else:
        email = None
        phone = None

    has_email = bool(email and str(email).strip())
    has_phone = bool(phone and str(phone).strip())

    if not has_email and not has_phone:
        flags.append({
            "code": "MISSING_CONTACT",
            "count": None,
            "field": "personal_info",
        })

    enriched["flags"] = flags

    return enriched
