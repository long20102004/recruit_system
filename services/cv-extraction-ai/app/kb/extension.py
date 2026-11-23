"""System skills and relations added on top of the generated public seed.

The generated CSV files stay untouched. These rows cover names the interview
bank and the matcher need, plus the family relations the small matcher graph used.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

TYPE_SKILLS = {
    "Frontend Framework",
    "Backend Framework",
    "Web Framework",
    "API",
    "Database",
    "Cloud Computing",
    "Data Science",
    "Shell Scripting",
}


def graph_key(text: str | None) -> str:
    """Shared skill id for the matcher and the interview service."""
    value = unicodedata.normalize("NFD", text or "")
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "d").lower()
    return re.sub(r"[^a-z0-9]", "", value)


def _by_name(skills: dict[int, tuple[str, str]]) -> dict[str, int]:
    return {name.casefold(): sid for sid, (name, _) in skills.items()}


def merge_extension(
    seed_dir: str | Path,
    skills: dict[int, tuple[str, str]],
    aliases: dict[str, int] | None = None,
    surfaces: dict[str, int] | None = None,
    edges: dict[int, list[tuple[str, int]]] | None = None,
) -> None:
    folder = Path(seed_dir) / "extensions"
    if not folder.is_dir():
        return
    skills_csv = folder / "skills.csv"
    if skills_csv.exists():
        with skills_csv.open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                sid = int(row["id"])
                name = row["name"].strip()
                if sid in skills or not name:
                    continue
                skills[sid] = (name, row.get("category", "").strip())
    names = _by_name(skills)
    alias_csv = folder / "skill_aliases.csv"
    if alias_csv.exists() and aliases is not None and surfaces is not None:
        from app.kb.keys import skill_key

        with alias_csv.open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                sid = names.get(row["skill_name"].strip().casefold())
                surface = row.get("surface", "").strip()
                if sid is None or not surface:
                    continue
                key = skill_key(surface)
                if key and key not in aliases:
                    aliases[key] = sid
                folded = surface.casefold()
                if folded not in surfaces:
                    surfaces[folded] = sid
    edge_csv = folder / "skill_edges.csv"
    if edge_csv.exists() and edges is not None:
        with edge_csv.open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                src = names.get(row["src_name"].strip().casefold())
                dst = names.get(row["dst_name"].strip().casefold())
                rel = row["rel"].strip()
                if src is None or dst is None or src == dst or not rel:
                    continue
                current = edges.setdefault(src, [])
                if (rel, dst) not in current:
                    current.append((rel, dst))
        for src in edges:
            edges[src].sort(key=lambda item: (item[0], item[1]))


def skills_mentioned(text: str, skills: dict[int, tuple[str, str]]) -> list[str]:
    """Skills whose name appears as a whole phrase in a job title or description."""
    from app.postprocess.text_match import normalize

    haystack = normalize(text)
    if not haystack:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for _sid, (name, category) in skills.items():
        if category == "Soft Skill" or name in TYPE_SKILLS:
            continue
        needle = normalize(name)
        if len(needle) < 3 or needle in seen:
            continue
        if re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", haystack):
            seen.add(needle)
            found.append(name)
    return found
