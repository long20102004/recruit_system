"""Measure KB skill and school entity-linking coverage on CV evaluation splits."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable

from app.kb.keys import school_key
from app.kb.linker import Link, SkillLinker
from eval.dataset import Sample, load_split

__all__ = ["measure_skills", "measure_schools", "run", "main"]

_METHODS: tuple[str, ...] = ("exact", "normalized", "fuzzy", "split", "unlinked")
_CIRCULARITY_CAVEAT: str = (
    "KB seeded from train labels only; val never used for seeding; "
    "coverage on same-distribution data is optimistic (circularity caveat)"
)


def measure_skills(
    samples: Iterable[Sample],
    linker: SkillLinker,
) -> dict[str, Any]:
    """Measure skill entity-linking breakdown across CV samples.

    For each sample, each entry in gold["skills"] (excluding tech_stack) is treated
    as one mention. Mentions are classified by their best link method:
    - If all links are unlinked (or no links returned) -> 'unlinked'
    - Else if any link has method 'split' -> 'split'
    - Else -> method of the first link ('exact', 'normalized', 'fuzzy')
    """
    counts: dict[str, int] = {m: 0 for m in _METHODS}
    distinct_skill_ids: set[int] = set()
    total = 0

    for sample in samples:
        gold = getattr(sample, "gold", None)
        if not isinstance(gold, dict):
            continue
        skill_items = gold.get("skills")
        if not isinstance(skill_items, (list, tuple)):
            continue

        for item in skill_items:
            if item is None:
                continue
            raw_text = str(item).strip()
            if not raw_text:
                continue

            total += 1
            links = linker.link(raw_text)

            for l in links:
                if l.skill_id is not None:
                    distinct_skill_ids.add(l.skill_id)

            if not links or all(l.method == "unlinked" for l in links):
                method = "unlinked"
            elif any(l.method == "split" for l in links):
                method = "split"
            else:
                method = links[0].method

            if method not in counts:
                counts[method] = 0
            counts[method] += 1

    shares: dict[str, float] = {
        m: (counts[m] / total) if total > 0 else 0.0
        for m in _METHODS
    }
    unlinked_share = shares.get("unlinked", 0.0)
    linked_share = (1.0 - unlinked_share) if total > 0 else 0.0

    result: dict[str, Any] = {
        "total": total,
        "counts": counts,
        "shares": shares,
        "linked_share": linked_share,
        "distinct_skills_linked": len(distinct_skill_ids),
        "unlinked_examples_count": counts.get("unlinked", 0),
    }
    # Provide top-level method counts for convenience
    for m in _METHODS:
        result[m] = counts[m]

    return result


def measure_schools(
    samples: Iterable[Sample],
    seed_dir: str | Path,
) -> dict[str, Any]:
    """Measure university / school linking share against KB university aliases."""
    seed_p = Path(seed_dir)
    alias_map: dict[str, int] = {}

    # If canonical universities.csv exists, index canonical names as base keys
    unis_csv = seed_p / "universities.csv"
    if unis_csv.exists():
        with unis_csv.open("r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("name", "").strip()
                uid_str = row.get("id", "").strip()
                if name and uid_str:
                    try:
                        k = school_key(name)
                        if k:
                            alias_map[k] = int(uid_str)
                    except ValueError:
                        pass

    # Read university_aliases.csv (alias_key -> university_id)
    aliases_csv = seed_p / "university_aliases.csv"
    if aliases_csv.exists():
        with aliases_csv.open("r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                ak = row.get("alias_key", "").strip()
                uid_str = row.get("university_id", "").strip()
                if ak and uid_str:
                    try:
                        alias_map[ak] = int(uid_str)
                    except ValueError:
                        pass

    total = 0
    linked = 0

    for sample in samples:
        gold = getattr(sample, "gold", None)
        if not isinstance(gold, dict):
            continue
        education = gold.get("education")
        if not isinstance(education, (list, tuple)):
            continue

        for edu in education:
            if not isinstance(edu, dict):
                continue
            school = edu.get("school")
            if not school or not isinstance(school, str):
                continue
            cleaned = school.strip()
            if not cleaned:
                continue

            total += 1
            k = school_key(cleaned)
            if k and k in alias_map:
                linked += 1

    share = (linked / total) if total > 0 else 0.0
    return {
        "total": total,
        "linked": linked,
        "share": share,
    }


def _format_markdown_report(
    n_cv: int,
    ms_per_cv: float,
    skill_stats: dict[str, Any],
    school_stats: dict[str, Any],
    csv_db_consistent: bool | None = None,
    csv_db_mismatches: int = 0,
) -> str:
    """Format evaluation coverage results into a Markdown report."""
    counts = skill_stats.get("counts", {})
    shares = skill_stats.get("shares", {})
    total_skills = skill_stats.get("total", 0)
    linked_share = skill_stats.get("linked_share", 0.0)
    distinct_skills = skill_stats.get("distinct_skills_linked", 0)
    unlinked_skills = skill_stats.get("unlinked_examples_count", 0)

    total_schools = school_stats.get("total", 0)
    linked_schools = school_stats.get("linked", 0)
    school_share = school_stats.get("share", 0.0)

    lines: list[str] = [
        "# KB Skill & School Linking Report",
        "",
        f"- **CV count (n)**: {n_cv}",
        f"- **Average latency**: {ms_per_cv:.3f} ms/CV",
        "",
        "## Skill Linking Breakdown",
        "",
        "| Method | Count | Share |",
        "| --- | --- | --- |",
        f"| exact | {counts.get('exact', 0)} | {shares.get('exact', 0.0):.2%} |",
        f"| normalized | {counts.get('normalized', 0)} | {shares.get('normalized', 0.0):.2%} |",
        f"| split | {counts.get('split', 0)} | {shares.get('split', 0.0):.2%} |",
        f"| fuzzy | {counts.get('fuzzy', 0)} | {shares.get('fuzzy', 0.0):.2%} |",
        f"| unlinked | {counts.get('unlinked', 0)} | {shares.get('unlinked', 0.0):.2%} |",
        f"| **Total** | **{total_skills}** | **100.00%** |",
        "",
        f"- **Linked Share**: {linked_share:.2%}",
        f"- **Distinct Skills Linked**: {distinct_skills}",
        f"- **Unlinked Mentions Count**: {unlinked_skills}",
        "",
        "## School Linking Breakdown",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Total Schools | {total_schools} |",
        f"| Linked Schools | {linked_schools} |",
        f"| Linking Share | {school_share:.2%} |",
        "",
    ]

    if csv_db_consistent is not None:
        lines.extend([
            "## Database vs CSV Consistency",
            "",
            f"- **Consistent**: {'Yes' if csv_db_consistent else 'No'}",
            f"- **Mismatches**: {csv_db_mismatches}",
            "",
        ])

    lines.extend([
        f"> {_CIRCULARITY_CAVEAT}",
        "",
    ])

    return "\n".join(lines)


def run(
    split_path: str | Path,
    seed_dir: str | Path,
    out_dir: str | Path,
    dsn: str | None = None,
) -> dict[str, Any]:
    """Execute evaluation linking coverage and write report files."""
    split_p = Path(split_path)
    seed_p = Path(seed_dir)
    out_p = Path(out_dir)

    samples = load_split(split_p)
    n_samples = len(samples)

    if dsn:
        linker = SkillLinker.from_db(dsn)
    else:
        linker = SkillLinker.from_csv(seed_p)

    csv_db_consistent: bool | None = None
    csv_db_mismatches = 0
    if dsn:
        csv_linker = SkillLinker.from_csv(seed_p)
        for s in samples:
            gold = getattr(s, "gold", None)
            if not isinstance(gold, dict):
                continue
            for item in gold.get("skills") or []:
                if item is None:
                    continue
                raw_text = str(item).strip()
                if not raw_text:
                    continue
                links_db = linker.link(raw_text)
                links_csv = csv_linker.link(raw_text)
                sig_db = [(l.skill_id, l.method) for l in links_db]
                sig_csv = [(l.skill_id, l.method) for l in links_csv]
                if sig_db != sig_csv:
                    csv_db_mismatches += 1
        csv_db_consistent = (csv_db_mismatches == 0)

    # Benchmark average linking time per CV
    t0 = time.perf_counter()
    for s in samples:
        gold = getattr(s, "gold", None)
        if not isinstance(gold, dict):
            continue
        for item in gold.get("skills") or []:
            if item is not None and str(item).strip():
                linker.link(str(item))
    t1 = time.perf_counter()
    ms_per_cv = ((t1 - t0) * 1000.0 / n_samples) if n_samples > 0 else 0.0

    skill_stats = measure_skills(samples, linker)
    school_stats = measure_schools(samples, seed_p)

    report_data: dict[str, Any] = {
        "n_cv": n_samples,
        "ms_per_cv": ms_per_cv,
        "skills": skill_stats,
        "schools": school_stats,
        "caveat": _CIRCULARITY_CAVEAT,
    }
    if dsn is not None:
        report_data["csv_db_consistent"] = csv_db_consistent
        report_data["csv_db_mismatches"] = csv_db_mismatches

    out_p.mkdir(parents=True, exist_ok=True)

    json_path = out_p / "linking_report.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    report_md = _format_markdown_report(
        n_cv=n_samples,
        ms_per_cv=ms_per_cv,
        skill_stats=skill_stats,
        school_stats=school_stats,
        csv_db_consistent=csv_db_consistent,
        csv_db_mismatches=csv_db_mismatches,
    )

    md_path = out_p / "linking_report.md"
    md_path.write_text(report_md, encoding="utf-8")

    # Print markdown report to console without printing raw CV/skill content
    print(report_md)

    return report_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure KB skill and school linking coverage on evaluation split."
    )
    parser.add_argument(
        "--split",
        default="data/clean/val.jsonl",
        help="Path to evaluation split JSONL (default: data/clean/val.jsonl)",
    )
    parser.add_argument(
        "--seed",
        default="kb/seed",
        help="Path to seed CSV directory (default: kb/seed)",
    )
    parser.add_argument(
        "--out",
        default="data/runs/kb",
        help="Output directory for reports (default: data/runs/kb)",
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("KB_DSN", None) or None,
        help="PostgreSQL DSN (optional, defaults to KB_DSN env var if set)",
    )
    args = parser.parse_args()

    run(
        split_path=args.split,
        seed_dir=args.seed,
        out_dir=args.out,
        dsn=args.dsn,
    )


if __name__ == "__main__":
    main()
