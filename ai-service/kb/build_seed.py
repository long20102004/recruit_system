"""Build KB seed CSV files from training dataset and curated vocabulary."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

from rapidfuzz import fuzz, process

from app.kb.keys import school_key, skill_key
from app.postprocess.skills import clean_skill_list
from app.postprocess.text_match import normalize
from eval.dataset import load_split
from kb.load import read_seed, validate

__all__ = ["CATEGORIES", "build_seed", "main"]

CATEGORIES: list[str] = [
    "Programming Language",
    "Framework/Library",
    "Frontend",
    "Mobile",
    "Database",
    "Cloud",
    "DevOps/CI-CD",
    "Testing/QA",
    "Data/AI",
    "Business Analysis",
    "Design/UI-UX",
    "Security",
    "Tool/Platform",
    "Methodology/Concept",
    "Soft Skill",
    "Other",
]

_CATEGORY_SET: set[str] = set(CATEGORIES)
_COMPOSITE_REGEX: re.Pattern[str] = re.compile(r"\s*/\s*|\s+&\s+|\s*\(")
_SPLIT_REGEX: re.Pattern[str] = re.compile(r"\s*/\s*|\s+&\s+|\s+and\s+|\s*[(),]\s*")
_SECTION_BLOCK_REGEX: re.Pattern[str] = re.compile(
    r"reg\(\s*CvSection\.(\w+)\s*,\s*(.*?)\);", re.DOTALL
)
_STRING_LITERAL_REGEX: re.Pattern[str] = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')


def _read_csv_rows(file_path: Path) -> list[dict[str, str]]:
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {
                (k.strip() if k else ""): (v.strip() if isinstance(v, str) else "")
                for k, v in row.items()
                if k is not None
            }
            rows.append(cleaned)
        return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _is_composite(surface: str, non_composite_keys: set[str]) -> bool:
    if not _COMPOSITE_REGEX.search(surface):
        return False
    parts = [p.strip(" \t(),") for p in _SPLIT_REGEX.split(surface)]
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return False
    part_keys = [skill_key(p) for p in parts]
    return all(bool(pk and pk in non_composite_keys) for pk in part_keys)



def _read_reference_universities(path: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Read the public university list (name_vi,name_en,abbreviation,group).

    Returns (name -> alias surfaces, unambiguous alias_key -> name). Alias keys that
    point to more than one university (e.g. shared abbreviations "DTU", or member
    names like "Trường Đại học Kinh tế" without their parent) are dropped.
    """
    if not path.exists():
        return {}, {}
    unis: dict[str, list[str]] = {}
    key_owners: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("name_vi") or "").strip()
            if not name:
                continue
            surfaces = [name]
            for col in ("name_en", "abbreviation"):
                v = (row.get(col) or "").strip()
                if v and v not in ("—", "-"):
                    surfaces.append(v)
            group = (row.get("group") or "").strip()
            if group and name.endswith(", " + group):
                surfaces.append(name[: -len(", " + group)])
            unis[name] = surfaces
            for s in surfaces:
                k = school_key(s)
                if k:
                    key_owners[k].add(name)
    alias = {k: next(iter(owners)) for k, owners in key_owners.items() if len(owners) == 1}
    unis = {n: [s for s in surfs if alias.get(school_key(s)) == n] for n, surfs in unis.items()}
    return unis, alias


# Rare keys (>= 5 chars) whose fuzz.ratio to a strictly more frequent key is >= this
# threshold are folded into that key as an alias (silver labels contain typos).
FUZZY_MERGE_THRESHOLD = 90


def _fuzzy_merge_targets(
    skill_groups: dict[str, dict[str, int]],
    non_composite_keys: set[str],
    keep_composite: dict[str, bool],
) -> dict[str, str]:
    """Map rare variant key -> final target key (chains resolved)."""
    freq = {k: sum(v.values()) for k, v in skill_groups.items()}
    eligible_targets = [k for k in freq if k in non_composite_keys or keep_composite.get(k)]
    merged: dict[str, str] = {}
    for k in sorted(freq, key=lambda x: (freq[x], x)):
        if len(k) < 5 or keep_composite.get(k):
            continue
        cands = [c for c in eligible_targets if c != k and freq[c] > freq[k]]
        if not cands:
            continue
        m = process.extractOne(k, cands, scorer=fuzz.ratio, score_cutoff=FUZZY_MERGE_THRESHOLD)
        if m:
            merged[k] = m[0]
    def final(k: str) -> str:
        seen = set()
        while k in merged and k not in seen:
            seen.add(k)
            k = merged[k]
        return k
    return {k: final(k) for k in merged}

def build_seed(
    train_path: str | Path,
    out_dir: str | Path,
    curated_dir: str | Path,
    section_dict_path: str | Path,
) -> dict[str, Any]:
    """Derive seed CSV files from train gold split and curated inputs."""
    train_p = Path(train_path)
    out_p = Path(out_dir)
    curated_p = Path(curated_dir)
    section_dict_p = Path(section_dict_path)

    out_p.mkdir(parents=True, exist_ok=True)

    # 1. Load train samples
    samples = load_split(train_p) if train_p.exists() else []

    all_cleaned_surfaces: list[str] = []
    for sample in samples:
        gold = sample.gold
        items_to_clean: list[str] = []
        if gold.get("skills"):
            items_to_clean.extend(gold["skills"])
        for proj in gold.get("personal_projects") or []:
            if proj.get("tech_stack"):
                items_to_clean.extend(proj["tech_stack"])
        cleaned = clean_skill_list(items_to_clean)
        all_cleaned_surfaces.extend(cleaned)

    # 2. Read curated files
    curated_categories: dict[str, str] = {}
    curated_keep_composite: dict[str, bool] = {}
    # "reviewed" = a person checked the curated row (LLM proposals stay false).
    curated_skill_reviewed: dict[str, bool] = {}
    cat_curated_path = curated_p / "skill_categories_curated.csv"
    for row in _read_csv_rows(cat_curated_path):
        key = row.get("key", "").strip()
        cat = row.get("category", "").strip()
        keep = row.get("keep_composite", "").strip().lower() in ("true", "1", "yes", "t")
        if key:
            curated_categories[key] = cat
            curated_keep_composite[key] = keep
            curated_skill_reviewed[key] = (str(row.get("reviewed", "")).strip().lower() in ("true", "1", "yes", "t"))

    curated_edges: list[dict[str, str]] = []
    edge_curated_path = curated_p / "skill_edges_curated.csv"
    for row in _read_csv_rows(edge_curated_path):
        src_name = row.get("src_name", "").strip()
        rel = row.get("rel", "").strip()
        dst_name = row.get("dst_name", "").strip()
        if src_name and rel and dst_name:
            curated_edges.append({"src_name": src_name, "rel": rel, "dst_name": dst_name})

    curated_universities: dict[str, tuple[str, list[str]]] = {}
    curated_uni_reviewed: dict[str, bool] = {}
    uni_curated_path = curated_p / "university_curated.csv"
    for row in _read_csv_rows(uni_curated_path):
        raw_key = row.get("key", "").strip()
        key = school_key(raw_key) if raw_key else ""
        canonical_name = row.get("canonical_name", "").strip()
        extra_aliases_raw = row.get("extra_aliases", "").strip()
        extra_aliases = [
            a.strip() for a in extra_aliases_raw.split("|") if a.strip()
        ]
        if key and canonical_name:
            curated_universities[key] = (canonical_name, extra_aliases)
            curated_uni_reviewed[canonical_name] = (str(row.get("reviewed", "")).strip().lower() in ("true", "1", "yes", "t"))

    # 3. Skills: group by skill_key, identify non-composite keys, filter composite
    non_composite_keys: set[str] = set()
    skill_groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for surface in all_cleaned_surfaces:
        surface_str = surface.strip()
        if not surface_str:
            continue
        k = skill_key(surface_str)
        if not k:
            continue
        skill_groups[k][surface_str] += 1
        if not _COMPOSITE_REGEX.search(surface_str):
            non_composite_keys.add(k)

    # 3b. Fold rare spelling variants into a more frequent key
    #     ("PostgreQl" -> PostgreSQL, "REST APIs" -> REST API, "Bootstrap 5" -> Bootstrap).
    merged_into = _fuzzy_merge_targets(skill_groups, non_composite_keys, curated_keep_composite)

    composites_dropped = 0
    kept_skills: list[dict[str, Any]] = []

    for k in sorted(skill_groups.keys()):
        if k in merged_into:
            continue
        surfaces_dict = skill_groups[k]
        canonical_name = min(
            surfaces_dict.keys(),
            key=lambda s: (-surfaces_dict[s], len(s), s),
        )

        keep_comp = curated_keep_composite.get(k, False)
        if not keep_comp and _is_composite(canonical_name, non_composite_keys):
            composites_dropped += 1
            continue

        if k in curated_categories:
            cat = curated_categories[k]
            if cat not in _CATEGORY_SET:
                raise ValueError(
                    f"Invalid category '{cat}' for skill key '{k}'. Must be one of {CATEGORIES}"
                )
            reviewed = "true" if curated_skill_reviewed.get(k) else "false"
        else:
            cat = "Other"
            reviewed = "false"

        kept_skills.append(
            {
                "key": k,
                "name": canonical_name,
                "category": cat,
                "reviewed": reviewed,
            }
        )

    # 4. skills.csv: id 1..N sorted by canonical name (casefold)
    kept_skills.sort(key=lambda s: (s["name"].casefold(), s["name"]))
    for idx, s in enumerate(kept_skills, start=1):
        s["id"] = idx

    skills_rows = [
        {
            "id": str(s["id"]),
            "name": s["name"],
            "category": s["category"],
            "reviewed": s["reviewed"],
        }
        for s in kept_skills
    ]
    _write_csv(
        out_p / "skills.csv",
        skills_rows,
        ["id", "name", "category", "reviewed"],
    )

    # 5. skill_aliases.csv: alias_key=key, skill_id, surface=canonical name
    alias_rows = [
        {
            "alias_key": s["key"],
            "skill_id": str(s["id"]),
            "surface": s["name"],
        }
        for s in kept_skills
    ]
    key_to_kept = {s["key"]: s for s in kept_skills}
    fuzzy_merged = 0
    for k, target in sorted(merged_into.items()):
        tgt = key_to_kept.get(target)
        if tgt is None:
            continue
        variant = min(skill_groups[k], key=lambda v: (-skill_groups[k][v], len(v), v))
        alias_rows.append({"alias_key": k, "skill_id": str(tgt["id"]), "surface": variant})
        fuzzy_merged += 1
    alias_rows.sort(key=lambda x: x["alias_key"])
    _write_csv(
        out_p / "skill_aliases.csv",
        alias_rows,
        ["alias_key", "skill_id", "surface"],
    )

    # 6. skill_edges.csv: match curated edges
    name_to_id: dict[str, int] = {s["name"].casefold(): s["id"] for s in kept_skills}
    key_to_id: dict[str, int] = {s["key"]: s["id"] for s in kept_skills}

    def resolve_skill_name(name: str) -> int | None:
        if not name:
            return None
        folded = name.casefold()
        if folded in name_to_id:
            return name_to_id[folded]
        k = skill_key(name)
        k = merged_into.get(k, k)
        if k and k in key_to_id:
            return key_to_id[k]
        return None

    edge_tuples: list[tuple[int, str, int]] = []
    edges_unresolved: list[str] = []
    seen_unresolved: set[str] = set()

    for edge in curated_edges:
        src_name = edge["src_name"]
        dst_name = edge["dst_name"]
        rel = edge["rel"]

        src_id = resolve_skill_name(src_name)
        dst_id = resolve_skill_name(dst_name)

        if src_id is None:
            if src_name not in seen_unresolved:
                seen_unresolved.add(src_name)
                edges_unresolved.append(src_name)
        if dst_id is None:
            if dst_name not in seen_unresolved:
                seen_unresolved.add(dst_name)
                edges_unresolved.append(dst_name)

        if src_id is not None and dst_id is not None and src_id != dst_id:
            edge_tuples.append((src_id, rel, dst_id))

    unique_edges = sorted(set(edge_tuples))
    edge_csv_rows = [
        {"src_id": str(src), "rel": rel, "dst_id": str(dst)}
        for src, rel, dst in unique_edges
    ]
    _write_csv(
        out_p / "skill_edges.csv",
        edge_csv_rows,
        ["src_id", "rel", "dst_id"],
    )

    # 7. Universities: gold education.school -> school_key
    school_surfaces: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for sample in samples:
        for edu in sample.gold.get("education") or []:
            raw_school = edu.get("school")
            if not raw_school or not isinstance(raw_school, str):
                continue
            cleaned = raw_school.strip()
            if not cleaned:
                continue
            k = school_key(cleaned)
            if not k:
                continue
            school_surfaces[k][cleaned] += 1

    alias_to_curated: dict[str, tuple[str, list[str]]] = {}
    for c_key, (c_name, extras) in curated_universities.items():
        alias_to_curated[c_key] = (c_name, extras)
        for extra in extras:
            ak = school_key(extra)
            if ak:
                alias_to_curated[ak] = (c_name, extras)

    # Universities are an OPEN set (like companies): the public reference list is a
    # normalisation dictionary, never a whitelist. Train schools that match it are
    # attached to the reference entry; the others are kept as their own entries.
    ref_unis, ref_alias = _read_reference_universities(curated_p / "vn_universities.csv")

    uni_by_canon: dict[str, dict[str, Any]] = {}
    for name, aliases in ref_unis.items():
        uni_by_canon[name] = {
            "name": name,
            "reviewed": False,
            "gold_keys": {},
            "extra_aliases": list(aliases),
        }

    for k in sorted(school_surfaces.keys()):
        surfaces_dict = school_surfaces[k]
        if k in alias_to_curated:
            c_name, extras = alias_to_curated[k]
            reviewed = curated_uni_reviewed.get(c_name, False)
            ref_name = next(
                (
                    ref_alias[x]
                    for x in [k, school_key(c_name)] + [school_key(e) for e in extras]
                    if x in ref_alias
                ),
                None,
            )
            if ref_name:
                c_name = ref_name
        elif k in ref_alias:
            c_name, extras, reviewed = ref_alias[k], [], False
        else:
            c_name = min(
                surfaces_dict.keys(),
                key=lambda s: (-surfaces_dict[s], len(s), s),
            )
            extras = []
            reviewed = False

        if c_name not in uni_by_canon:
            uni_by_canon[c_name] = {
                "name": c_name,
                "reviewed": reviewed,
                "gold_keys": {k: surfaces_dict},
                "extra_aliases": list(extras),
            }
        else:
            uni_by_canon[c_name]["gold_keys"][k] = surfaces_dict
            if reviewed:
                uni_by_canon[c_name]["reviewed"] = True
            for extra in extras:
                if extra not in uni_by_canon[c_name]["extra_aliases"]:
                    uni_by_canon[c_name]["extra_aliases"].append(extra)

    sorted_unis = sorted(
        uni_by_canon.values(), key=lambda u: (u["name"].casefold(), u["name"])
    )
    for idx, u in enumerate(sorted_unis, start=1):
        u["id"] = idx

    uni_csv_rows = [
        {
            "id": str(u["id"]),
            "name": u["name"],
            "reviewed": "true" if u["reviewed"] else "false",
        }
        for u in sorted_unis
    ]
    _write_csv(
        out_p / "universities.csv",
        uni_csv_rows,
        ["id", "name", "reviewed"],
    )

    uni_alias_rows: list[dict[str, str]] = []
    seen_uni_aliases: set[str] = set()

    for u in sorted_unis:
        uid_str = str(u["id"])
        # Gold aliases
        for k in sorted(u["gold_keys"].keys()):
            s_dict = u["gold_keys"][k]
            surf = min(s_dict.keys(), key=lambda s: (-s_dict[s], len(s), s))
            if k and k not in seen_uni_aliases:
                seen_uni_aliases.add(k)
                uni_alias_rows.append(
                    {"alias_key": k, "university_id": uid_str, "surface": surf}
                )
        # Extra aliases
        for extra in u["extra_aliases"]:
            ak = school_key(extra)
            if ak and ak not in seen_uni_aliases:
                seen_uni_aliases.add(ak)
                uni_alias_rows.append(
                    {"alias_key": ak, "university_id": uid_str, "surface": extra}
                )

    uni_alias_rows.sort(key=lambda x: x["alias_key"])
    _write_csv(
        out_p / "university_aliases.csv",
        uni_alias_rows,
        ["alias_key", "university_id", "surface"],
    )

    # 8. Job Titles: gold experience.job_title -> normalize(title)
    title_surfaces: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for sample in samples:
        for exp in sample.gold.get("experience") or []:
            raw_title = exp.get("job_title")
            if not raw_title or not isinstance(raw_title, str):
                continue
            cleaned = raw_title.strip()
            if not cleaned:
                continue
            k = normalize(cleaned)
            if not k:
                continue
            title_surfaces[k][cleaned] += 1

    job_titles: list[dict[str, str]] = []
    for k in sorted(title_surfaces.keys()):
        surfaces_dict = title_surfaces[k]
        canon = min(
            surfaces_dict.keys(),
            key=lambda s: (-surfaces_dict[s], len(s), s),
        )
        job_titles.append({"name": canon, "alias_key": k})

    job_titles.sort(key=lambda x: (x["name"].casefold(), x["name"]))
    for idx, jt in enumerate(job_titles, start=1):
        jt["id"] = str(idx)

    jt_csv_rows = [
        {"id": jt["id"], "name": jt["name"], "alias_key": jt["alias_key"]}
        for jt in job_titles
    ]
    _write_csv(
        out_p / "job_titles.csv",
        jt_csv_rows,
        ["id", "name", "alias_key"],
    )

    # 9. Section Headings: parse Java SectionDictionary
    section_headings: list[dict[str, str]] = []
    seen_headings: set[str] = set()

    # Fallback paths for running from either ai-service or repository root
    resolved_sec_path = section_dict_p
    if not resolved_sec_path.exists():
        cand1 = Path("..") / section_dict_p
        cand2 = Path("backend/src/main/java/recruit/demo/extraction/section/SectionDictionary.java")
        if cand1.exists():
            resolved_sec_path = cand1
        elif cand2.exists():
            resolved_sec_path = cand2

    if resolved_sec_path.exists():
        java_content = resolved_sec_path.read_text(encoding="utf-8")
        for match in _SECTION_BLOCK_REGEX.finditer(java_content):
            section_name = match.group(1).strip()
            block_text = match.group(2)
            literals = _STRING_LITERAL_REGEX.findall(block_text)
            for lit in literals:
                heading = lit.strip()
                if not heading:
                    continue
                if heading not in seen_headings:
                    seen_headings.add(heading)
                    section_headings.append(
                        {"heading": heading, "section": section_name}
                    )

    section_headings.sort(key=lambda x: x["heading"])
    _write_csv(
        out_p / "section_headings.csv",
        section_headings,
        ["heading", "section"],
    )

    # 10. categories.csv (id, name)
    category_rows = [
        {"id": str(idx), "name": cat_name}
        for idx, cat_name in enumerate(CATEGORIES, start=1)
    ]
    _write_csv(out_p / "categories.csv", category_rows, ["id", "name"])

    # 11. Validate written seed files
    seed_data = read_seed(out_p)
    validation_errors = validate(seed_data)
    if validation_errors:
        raise ValueError(
            f"Seed validation failed with {len(validation_errors)} error(s):\n"
            + "\n".join(f"- {e}" for e in validation_errors)
        )

    summary: dict[str, Any] = {
        "skills": len(kept_skills),
        "aliases": len(alias_rows),
        "composites_dropped": composites_dropped,
        "fuzzy_merged": fuzzy_merged,
        "skills_reviewed": sum(1 for s in kept_skills if s["reviewed"] == "true"),
        "edges": len(unique_edges),
        "edges_unresolved": edges_unresolved,
        "universities": len(sorted_unis),
        "job_titles": len(job_titles),
        "section_headings": len(section_headings),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build KB seed CSV files from train split and curated vocabulary."
    )
    parser.add_argument(
        "--train",
        default="data/clean/train.jsonl",
        help="Path to cleaned train JSONL split",
    )
    parser.add_argument(
        "--out",
        default="kb/seed",
        help="Output directory for seed CSV files",
    )
    parser.add_argument(
        "--curated",
        default="kb/seed",
        help="Directory containing curated CSV files",
    )
    parser.add_argument(
        "--section-dict",
        default="../backend/src/main/java/recruit/demo/extraction/section/SectionDictionary.java",
        help="Path to SectionDictionary.java",
    )
    args = parser.parse_args()

    summary = build_seed(
        train_path=args.train,
        out_dir=args.out,
        curated_dir=args.curated,
        section_dict_path=args.section_dict,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
