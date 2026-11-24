"""Silver dataset cleaner for group-labeled skills (US1).

Strips group labels (e.g. 'Backend: ...', 'Tools: ...') from skill lists
and project tech stacks, splitting top-level composite items while preserving
uninfected items byte-for-byte and in their original order.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
from typing import Any

from app.postprocess.skills import clean_skill_list

# Matches infected items like "Backend: Spring Boot, Node.js".
# Group label must be 1-40 chars without ':', '(', ')', or newline, followed by ':'
# and at least one non-whitespace character.
INFECTED_PATTERN = re.compile(r"^\s*[^:()\n]{1,40}:\s*\S")


def is_infected(item: Any) -> bool:
    """Check if an item matches the group-label infection pattern."""
    if not isinstance(item, str):
        return False
    return bool(INFECTED_PATTERN.match(item))


def _clean_item_list(items: list[Any]) -> tuple[list[Any], int, int]:
    """Clean infected items in a list (skills or tech_stack).

    Returns:
        (new_list, items_stripped, items_added)
        where:
          - items_stripped: count of infected items replaced.
          - items_added: (total new items produced) - items_stripped.
        If no item is infected, returns (items, 0, 0) unchanged.
    """
    if not any(is_infected(x) for x in items):
        return items, 0, 0

    new_list: list[Any] = []
    items_stripped = 0
    items_produced = 0

    for x in items:
        if is_infected(x):
            items_stripped += 1
            produced = clean_skill_list([x])
            items_produced += len(produced)
            new_list.extend(produced)
        else:
            new_list.append(x)

    items_added = items_produced - items_stripped
    return new_list, items_stripped, items_added


def clean_record(rec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Clean infected group labels in rec['output']['skills'] and project tech_stacks.

    Returns:
        (cleaned_rec, stats)
        where stats has keys:
          - 'changed': bool
          - 'items_stripped': int
          - 'items_added': int
        If unchanged, returns the exact original rec object.
    """
    stats_unchanged = {"changed": False, "items_stripped": 0, "items_added": 0}

    if not isinstance(rec, dict):
        return rec, stats_unchanged

    output_raw = rec.get("output")
    is_str = False

    if isinstance(output_raw, str):
        is_str = True
        try:
            parsed_output = json.loads(output_raw)
        except Exception:
            return rec, stats_unchanged
    elif isinstance(output_raw, dict):
        is_str = False
        parsed_output = copy.deepcopy(output_raw)
    else:
        return rec, stats_unchanged

    if not isinstance(parsed_output, dict):
        return rec, stats_unchanged

    total_stripped = 0
    total_added = 0

    # 1. Clean output["skills"] if list
    skills = parsed_output.get("skills")
    if isinstance(skills, list):
        cleaned_skills, s_stripped, s_added = _clean_item_list(skills)
        if s_stripped > 0:
            parsed_output["skills"] = cleaned_skills
            total_stripped += s_stripped
            total_added += s_added

    # 2. Clean each personal_projects item's tech_stack if list
    projects = parsed_output.get("personal_projects")
    if isinstance(projects, list):
        projects_modified = False
        new_projects = []
        for proj in projects:
            if isinstance(proj, dict) and isinstance(proj.get("tech_stack"), list):
                cleaned_stack, p_stripped, p_added = _clean_item_list(proj["tech_stack"])
                if p_stripped > 0:
                    projects_modified = True
                    total_stripped += p_stripped
                    total_added += p_added
                    proj_copy = dict(proj)
                    proj_copy["tech_stack"] = cleaned_stack
                    new_projects.append(proj_copy)
                else:
                    new_projects.append(proj)
            else:
                new_projects.append(proj)
        if projects_modified:
            parsed_output["personal_projects"] = new_projects

    if total_stripped == 0:
        return rec, stats_unchanged

    new_rec = dict(rec)
    if is_str:
        new_rec["output"] = json.dumps(parsed_output, ensure_ascii=False)
    else:
        new_rec["output"] = parsed_output

    stats = {
        "changed": True,
        "items_stripped": total_stripped,
        "items_added": total_added,
    }
    return new_rec, stats


def clean_file(in_path: str | Path, out_path: str | Path) -> dict[str, int]:
    """Clean a silver JSONL file line-by-line, writing byte-identical lines for unchanged records.

    Returns summary:
        {"records": n, "records_changed": k, "items_stripped": s, "items_added": a}
    """
    in_path = Path(in_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "records": 0,
        "records_changed": 0,
        "items_stripped": 0,
        "items_added": 0,
    }

    with in_path.open("r", encoding="utf-8") as in_f, out_path.open("w", encoding="utf-8") as out_f:
        for line in in_f:
            line_str = line.strip()
            if not line_str:
                out_f.write(line)
                continue

            summary["records"] += 1
            try:
                rec = json.loads(line_str)
            except Exception:
                out_f.write(line)
                continue

            if not isinstance(rec, dict):
                out_f.write(line)
                continue

            cleaned_rec, stats = clean_record(rec)
            if not stats["changed"]:
                out_f.write(line)
            else:
                summary["records_changed"] += 1
                summary["items_stripped"] += stats["items_stripped"]
                summary["items_added"] += stats["items_added"]
                ending = "\r\n" if line.endswith("\r\n") else "\n"
                out_f.write(json.dumps(cleaned_rec, ensure_ascii=False) + ending)

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean infected group labels in silver dataset.")
    parser.add_argument(
        "--in",
        dest="in_files",
        nargs="+",
        required=True,
        help="Input JSONL file(s)",
    )
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        required=True,
        help="Output directory",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files_summary: dict[str, dict[str, int]] = {}
    total_summary = {
        "records": 0,
        "records_changed": 0,
        "items_stripped": 0,
        "items_added": 0,
    }

    for path_str in args.in_files:
        in_p = Path(path_str)
        out_p = out_dir / in_p.name
        summary = clean_file(in_p, out_p)
        files_summary[str(in_p)] = summary

        total_summary["records"] += summary["records"]
        total_summary["records_changed"] += summary["records_changed"]
        total_summary["items_stripped"] += summary["items_stripped"]
        total_summary["items_added"] += summary["items_added"]

    result = {
        "files": files_summary,
        "total": total_summary,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
