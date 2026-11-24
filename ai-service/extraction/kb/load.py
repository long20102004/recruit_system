"""Knowledge Base schema management and seed loader for PostgreSQL."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import os
from pathlib import Path
import sys
from typing import Any

import psycopg

__all__ = ["read_seed", "validate", "load", "main"]

REQUIRED_SEED_FILES = {
    "categories": "categories.csv",
    "skills": "skills.csv",
}

OPTIONAL_SEED_FILES = {
    "skill_aliases": "skill_aliases.csv",
    "skill_edges": "skill_edges.csv",
    "universities": "universities.csv",
    "university_aliases": "university_aliases.csv",
    "job_titles": "job_titles.csv",
    "section_headings": "section_headings.csv",
}

ALLOWED_EDGE_RELS = {"PART_OF", "REQUIRES"}

TABLES = [
    "category",
    "skill",
    "skill_alias",
    "skill_edge",
    "university",
    "university_alias",
    "job_title",
    "job_title_skill",
    "section_heading",
]


def _read_csv_rows(file_path: Path) -> list[dict[str, str]]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {
                (k.strip() if k else ""): (v.strip() if isinstance(v, str) else "")
                for k, v in row.items()
                if k is not None
            }
            rows.append(cleaned)
        return rows


def read_seed(seed_dir: str | Path) -> dict[str, list[dict[str, str]]]:
    """Read seed CSV files from directory.

    Requires categories.csv and skills.csv. Missing optional CSVs return empty lists.
    """
    path = Path(seed_dir)
    seed: dict[str, list[dict[str, str]]] = {}

    for key, filename in REQUIRED_SEED_FILES.items():
        file_path = path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Required seed file missing: {file_path}")
        seed[key] = _read_csv_rows(file_path)

    for key, filename in OPTIONAL_SEED_FILES.items():
        file_path = path / filename
        if file_path.exists():
            seed[key] = _read_csv_rows(file_path)
        else:
            seed[key] = []

    # Check job_title_skill or job_title_skills
    jts_file = path / "job_title_skill.csv"
    if not jts_file.exists():
        jts_file = path / "job_title_skills.csv"
    if jts_file.exists():
        seed["job_title_skills"] = _read_csv_rows(jts_file)
    else:
        seed["job_title_skills"] = []

    return seed


def _detect_cycles(edges: list[tuple[int, int]]) -> list[list[int]]:
    """Detect cycles in a directed graph using DFS.

    Returns a list of cycle paths, e.g. [[1, 2, 1]].
    """
    adj: dict[int, list[int]] = defaultdict(list)
    nodes: set[int] = set()
    for u, v in edges:
        adj[u].append(v)
        nodes.add(u)
        nodes.add(v)

    # 0 = unvisited, 1 = visiting, 2 = visited
    state: dict[int, int] = {node: 0 for node in nodes}
    cycles: list[list[int]] = []

    def dfs(u: int, path: list[int]) -> None:
        state[u] = 1
        path.append(u)
        for v in adj[u]:
            if state[v] == 1:
                try:
                    idx = path.index(v)
                    cycles.append(path[idx:] + [v])
                except ValueError:
                    cycles.append([u, v])
            elif state[v] == 0:
                dfs(v, path)
        path.pop()
        state[u] = 2

    for node in sorted(nodes):
        if state[node] == 0:
            dfs(node, [])

    return cycles


def validate(seed: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Validate seed data in pure Python without database connection.

    Returns a list of error descriptions (empty list if valid).
    """
    errors: list[str] = []

    # 1. Categories
    cat_ids: set[int] = set()
    cat_names: set[str] = set()
    for r in seed.get("categories", []):
        try:
            cid = int(r["id"])
            if cid in cat_ids:
                errors.append(f"Duplicate category id: {cid}")
            cat_ids.add(cid)
        except (KeyError, ValueError):
            errors.append(f"Invalid or missing category id: {r.get('id')}")

        name = r.get("name", "").strip()
        if not name:
            errors.append(f"Empty category name for id {r.get('id')}")
        elif name in cat_names:
            errors.append(f"Duplicate category name: '{name}'")
        else:
            cat_names.add(name)

    # 2. Skills
    skill_ids: set[int] = set()
    skill_names: set[str] = set()
    for r in seed.get("skills", []):
        try:
            sid = int(r["id"])
            if sid in skill_ids:
                errors.append(f"Duplicate skill id: {sid}")
            skill_ids.add(sid)
        except (KeyError, ValueError):
            errors.append(f"Invalid or missing skill id: {r.get('id')}")

        name = r.get("name", "").strip()
        if not name:
            errors.append(f"Empty skill name for id {r.get('id')}")
        elif name in skill_names:
            errors.append(f"Duplicate skill name: '{name}'")
        else:
            skill_names.add(name)

        cat = r.get("category", "").strip()
        if cat not in cat_names:
            errors.append(f"Skill '{name}' has unknown category '{cat}'")

    # 3. Skill Aliases
    skill_alias_keys: set[str] = set()
    for r in seed.get("skill_aliases", []):
        alias_key = r.get("alias_key", "").strip()
        if not alias_key:
            errors.append("Empty alias_key in skill_aliases")
        elif alias_key in skill_alias_keys:
            errors.append(f"Duplicate skill alias_key: '{alias_key}'")
        else:
            skill_alias_keys.add(alias_key)

        try:
            target_skill_id = int(r["skill_id"])
            if target_skill_id not in skill_ids:
                errors.append(
                    f"Skill alias '{alias_key}' references non-existent skill_id {target_skill_id}"
                )
        except (KeyError, ValueError):
            errors.append(
                f"Skill alias '{alias_key}' has invalid skill_id: {r.get('skill_id')}"
            )

    # 4. Skill Edges
    edges_by_rel: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for r in seed.get("skill_edges", []):
        rel = r.get("rel", "").strip()
        if rel not in ALLOWED_EDGE_RELS:
            errors.append(
                f"Invalid skill edge relation '{rel}'. Allowed: {sorted(ALLOWED_EDGE_RELS)}"
            )

        src_id: int | None = None
        dst_id: int | None = None

        try:
            src_id = int(r["src_id"])
            if src_id not in skill_ids:
                errors.append(f"Skill edge src_id {src_id} does not exist in skills")
        except (KeyError, ValueError):
            errors.append(f"Skill edge has invalid src_id: {r.get('src_id')}")

        try:
            dst_id = int(r["dst_id"])
            if dst_id not in skill_ids:
                errors.append(f"Skill edge dst_id {dst_id} does not exist in skills")
        except (KeyError, ValueError):
            errors.append(f"Skill edge has invalid dst_id: {r.get('dst_id')}")

        if src_id is not None and dst_id is not None:
            if src_id == dst_id:
                errors.append(f"Skill edge self-loop detected: src_id {src_id} == dst_id {dst_id}")
            elif rel in ALLOWED_EDGE_RELS:
                edges_by_rel[rel].append((src_id, dst_id))

    # Cycle detection per relation
    for rel, edges in edges_by_rel.items():
        cycles = _detect_cycles(edges)
        for cycle in cycles:
            cycle_str = " -> ".join(map(str, cycle))
            errors.append(f"Cycle detected in relation '{rel}': {cycle_str}")

    # 5. Universities
    uni_ids: set[int] = set()
    uni_names: set[str] = set()
    for r in seed.get("universities", []):
        try:
            uid = int(r["id"])
            if uid in uni_ids:
                errors.append(f"Duplicate university id: {uid}")
            uni_ids.add(uid)
        except (KeyError, ValueError):
            errors.append(f"Invalid or missing university id: {r.get('id')}")

        name = r.get("name", "").strip()
        if not name:
            errors.append(f"Empty university name for id {r.get('id')}")
        elif name in uni_names:
            errors.append(f"Duplicate university name: '{name}'")
        else:
            uni_names.add(name)

    # 6. University Aliases
    uni_alias_keys: set[str] = set()
    for r in seed.get("university_aliases", []):
        alias_key = r.get("alias_key", "").strip()
        if not alias_key:
            errors.append("Empty alias_key in university_aliases")
        elif alias_key in uni_alias_keys:
            errors.append(f"Duplicate university alias_key: '{alias_key}'")
        else:
            uni_alias_keys.add(alias_key)

        try:
            target_uni_id = int(r["university_id"])
            if target_uni_id not in uni_ids:
                errors.append(
                    f"University alias '{alias_key}' references non-existent university_id {target_uni_id}"
                )
        except (KeyError, ValueError):
            errors.append(
                f"University alias '{alias_key}' has invalid university_id: {r.get('university_id')}"
            )

    # 7. Job Titles
    jt_ids: set[int] = set()
    jt_names: set[str] = set()
    jt_alias_keys: set[str] = set()
    for r in seed.get("job_titles", []):
        try:
            jid = int(r["id"])
            if jid in jt_ids:
                errors.append(f"Duplicate job_title id: {jid}")
            jt_ids.add(jid)
        except (KeyError, ValueError):
            errors.append(f"Invalid or missing job_title id: {r.get('id')}")

        name = r.get("name", "").strip()
        if not name:
            errors.append(f"Empty job_title name for id {r.get('id')}")
        elif name in jt_names:
            errors.append(f"Duplicate job_title name: '{name}'")
        else:
            jt_names.add(name)

        alias_key = r.get("alias_key", "").strip()
        if not alias_key:
            errors.append(f"Empty job_title alias_key for id {r.get('id')}")
        elif alias_key in jt_alias_keys:
            errors.append(f"Duplicate job_title alias_key: '{alias_key}'")
        else:
            jt_alias_keys.add(alias_key)

    # 8. Section Headings
    headings: set[str] = set()
    for r in seed.get("section_headings", []):
        h = r.get("heading", "").strip()
        if not h:
            errors.append("Empty heading in section_headings")
        elif h in headings:
            errors.append(f"Duplicate section_heading heading: '{h}'")
        else:
            headings.add(h)

    return errors


def _to_bool(val: Any) -> bool:
    return str(val).strip().lower() in ("true", "1", "t", "yes")


def load(
    dsn: str,
    seed_dir: str | Path,
    schema_path: str | Path,
) -> dict[str, int]:
    """Validate seeds and load them into PostgreSQL within a single transaction."""
    seed_path = Path(seed_dir)
    schema_file = Path(schema_path)

    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    seed = read_seed(seed_path)
    errors = validate(seed)
    if errors:
        error_msg = f"Seed validation failed with {len(errors)} error(s):\n" + "\n".join(
            f"- {e}" for e in errors
        )
        raise ValueError(error_msg)

    schema_sql = schema_file.read_text(encoding="utf-8")

    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                # 1. Apply schema
                cur.execute(schema_sql)
                # Apply additive migrations before loading source-bearing snapshots.
                migration = Path(__file__).resolve().parent / "sql" / "002_source.sql"
                cur.execute(migration.read_text(encoding="utf-8"))

                # 2. Truncate existing data
                cur.execute(
                    "TRUNCATE category, skill, skill_alias, skill_edge, "
                    "university, university_alias, job_title, job_title_skill, section_heading "
                    "RESTART IDENTITY CASCADE;"
                )

                # 3. Categories
                cat_rows = [(int(r["id"]), r["name"]) for r in seed["categories"]]
                cur.executemany(
                    "INSERT INTO category (id, name) VALUES (%s, %s);",
                    cat_rows,
                )
                cur.execute(
                    "SELECT setval(pg_get_serial_sequence('category', 'id'), COALESCE(MAX(id), 1)) FROM category;"
                )
                category_map = {r["name"]: int(r["id"]) for r in seed["categories"]}

                # 4. Skills
                skill_rows = [
                    (
                        int(r["id"]),
                        r["name"],
                        category_map[r["category"]],
                        _to_bool(r.get("reviewed", False)),
                        r.get("source", ""),
                    )
                    for r in seed["skills"]
                ]
                cur.executemany(
                    "INSERT INTO skill (id, name, category_id, reviewed, source) VALUES (%s, %s, %s, %s, %s);",
                    skill_rows,
                )

                # 5. Skill Aliases
                if seed.get("skill_aliases"):
                    alias_rows = [
                        (r["alias_key"], int(r["skill_id"]), r["surface"], r.get("source", ""))
                        for r in seed["skill_aliases"]
                    ]
                    cur.executemany(
                        "INSERT INTO skill_alias (alias_key, skill_id, surface, source) VALUES (%s, %s, %s, %s);",
                        alias_rows,
                    )

                # 6. Skill Edges
                if seed.get("skill_edges"):
                    edge_rows = [
                        (int(r["src_id"]), r["rel"], int(r["dst_id"]), r.get("source", ""))
                        for r in seed["skill_edges"]
                    ]
                    cur.executemany(
                        "INSERT INTO skill_edge (src_id, rel, dst_id, source) VALUES (%s, %s, %s, %s);",
                        edge_rows,
                    )

                # 7. Universities
                if seed.get("universities"):
                    uni_rows = [
                        (int(r["id"]), r["name"], _to_bool(r.get("reviewed", False)), r.get("source", ""))
                        for r in seed["universities"]
                    ]
                    cur.executemany(
                        "INSERT INTO university (id, name, reviewed, source) VALUES (%s, %s, %s, %s);",
                        uni_rows,
                    )

                # 8. University Aliases
                if seed.get("university_aliases"):
                    uni_alias_rows = [
                        (r["alias_key"], int(r["university_id"]), r.get("surface", ""), r.get("source", ""))
                        for r in seed["university_aliases"]
                    ]
                    cur.executemany(
                        "INSERT INTO university_alias (alias_key, university_id, surface, source) VALUES (%s, %s, %s, %s);",
                        uni_alias_rows,
                    )

                # 9. Job Titles
                if seed.get("job_titles"):
                    jt_rows = [
                        (int(r["id"]), r["name"], r["alias_key"], r.get("source", ""))
                        for r in seed["job_titles"]
                    ]
                    cur.executemany(
                        "INSERT INTO job_title (id, name, alias_key, source) VALUES (%s, %s, %s, %s);",
                        jt_rows,
                    )

                # 10. Job Title Skills
                jts = seed.get("job_title_skills") or []
                if jts:
                    jts_rows = [
                        (
                            int(r["job_title_id"]),
                            int(r["skill_id"]),
                            float(r.get("weight", 1.0)),
                        )
                        for r in jts
                    ]
                    cur.executemany(
                        "INSERT INTO job_title_skill (job_title_id, skill_id, weight) VALUES (%s, %s, %s);",
                        jts_rows,
                    )

                # 11. Section Headings
                if seed.get("section_headings"):
                    sh_rows = [
                        (r["heading"], r["section"])
                        for r in seed["section_headings"]
                    ]
                    cur.executemany(
                        "INSERT INTO section_heading (heading, section) VALUES (%s, %s);",
                        sh_rows,
                    )

                # Post-check: ensure zero orphaned skills
                cur.execute(
                    "SELECT count(*) FROM skill s LEFT JOIN category c ON s.category_id = c.id WHERE c.id IS NULL;"
                )
                orphans = cur.fetchone()[0]
                if orphans > 0:
                    raise RuntimeError(f"Post-check failed: {orphans} skills have no valid category")

                # Counts
                counts: dict[str, int] = {}
                for table in TABLES:
                    cur.execute(f"SELECT count(*) FROM {table};")
                    counts[table] = cur.fetchone()[0]

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Load KB seed CSVs into PostgreSQL.")
    parser.add_argument(
        "--dsn",
        default=os.environ.get("KB_DSN", ""),
        help="PostgreSQL DSN (defaults to KB_DSN env var)",
    )
    parser.add_argument(
        "--seed",
        default="kb/seed",
        help="Directory containing seed CSV files (default: kb/seed)",
    )
    parser.add_argument(
        "--schema",
        default="kb/sql/001_schema.sql",
        help="Path to schema SQL file (default: kb/sql/001_schema.sql)",
    )
    args = parser.parse_args()

    if not args.dsn:
        sys.stderr.write("Error: DSN not provided (use --dsn or set KB_DSN env var).\n")
        sys.exit(1)

    seed_path = Path(args.seed)
    if not seed_path.exists():
        fallback = Path(__file__).resolve().parent / "seed"
        if fallback.exists():
            seed_path = fallback

    schema_path = Path(args.schema)
    if not schema_path.exists():
        fallback = Path(__file__).resolve().parent / "sql" / "001_schema.sql"
        if fallback.exists():
            schema_path = fallback

    try:
        counts = load(dsn=args.dsn, seed_dir=seed_path, schema_path=schema_path)
        print(json.dumps(counts, indent=2))
    except Exception as e:
        sys.stderr.write(f"Error loading KB: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
