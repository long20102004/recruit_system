"""Load KB1 (books) and KB2 (seed CSVs) into Neo4j Knowledge Graph."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

# Ensure ai-service root is on sys.path
_AI_SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

from app.kb.keys import skill_key
from kb.load import read_seed

CONSTRAINTS = [
    ("Skill", "id", "skill_id_unique"),
    ("Category", "name", "category_name_unique"),
    ("Alias", "key", "alias_key_unique"),
    ("University", "id", "university_id_unique"),
    ("UniversityAlias", "key", "university_alias_key_unique"),
    ("JobTitle", "id", "job_title_id_unique"),
    ("Book", "id", "book_id_unique"),
    ("Section", "id", "section_id_unique"),
]


def _batch(items: list[Any], batch_size: int = 500) -> list[list[Any]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def create_constraints(session: Any) -> None:
    """Create unique constraints for all graph entities (Neo4j 5 syntax)."""
    for label, prop, name in CONSTRAINTS:
        query = (
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )
        session.run(query)


def reset_database(session: Any) -> None:
    """Detach delete all nodes in the database."""
    session.run("MATCH (n) DETACH DELETE n")


def load_kb2(session: Any, seed_dir: Path) -> dict[str, int]:
    """Load KB2 seed data into Neo4j using UNWIND + MERGE in batches."""
    seed = read_seed(seed_dir)
    stats: dict[str, int] = {}

    # 1. Categories
    categories = [
        {"name": r["name"].strip(), "source": r.get("source", "").strip()}
        for r in seed.get("categories", [])
        if r.get("name", "").strip()
    ]
    cat_query = """
    UNWIND $batch AS row
    MERGE (c:Category {name: row.name})
    SET c:KB2, c.source = row.source
    """
    for chunk in _batch(categories):
        session.run(cat_query, batch=chunk)
    stats["categories"] = len(categories)

    # 2. Skills + Category links
    skills = []
    for r in seed.get("skills", []):
        try:
            sid = int(r["id"])
            skills.append({
                "id": sid,
                "name": r["name"].strip(),
                "category": r.get("category", "").strip(),
                "source": r.get("source", "").strip(),
                "source_id": r.get("source_id", "").strip(),
            })
        except (KeyError, ValueError):
            continue

    skill_query = """
    UNWIND $batch AS row
    MERGE (s:Skill {id: row.id})
    SET s:KB2, s.name = row.name, s.category = row.category,
        s.source = row.source, s.source_id = row.source_id
    WITH s, row
    WHERE row.category <> ''
    MERGE (c:Category {name: row.category})
    SET c:KB2
    MERGE (s)-[:IN_CATEGORY]->(c)
    """
    for chunk in _batch(skills):
        session.run(skill_query, batch=chunk)
    stats["skills"] = len(skills)

    # 3. Aliases
    aliases = []
    for r in seed.get("skill_aliases", []):
        ak = r.get("alias_key", "").strip()
        try:
            sid = int(r["skill_id"])
            if ak:
                aliases.append({
                    "key": ak,
                    "skill_id": sid,
                    "surface": r.get("surface", "").strip(),
                    "source": r.get("source", "").strip(),
                })
        except (KeyError, ValueError):
            continue

    alias_query = """
    UNWIND $batch AS row
    MERGE (a:Alias {key: row.key})
    SET a:KB2, a.surface = row.surface, a.source = row.source
    WITH a, row
    MATCH (s:Skill {id: row.skill_id})
    MERGE (a)-[:ALIAS_OF]->(s)
    """
    for chunk in _batch(aliases):
        session.run(alias_query, batch=chunk)
    stats["aliases"] = len(aliases)

    # 4. Skill Edges (REQUIRES, PART_OF)
    requires_edges = []
    part_of_edges = []
    for r in seed.get("skill_edges", []):
        try:
            src_id = int(r["src_id"])
            dst_id = int(r["dst_id"])
            rel = r.get("rel", "").strip()
            source = r.get("source", "").strip()
            entry = {"src_id": src_id, "dst_id": dst_id, "source": source}
            if rel == "REQUIRES":
                requires_edges.append(entry)
            elif rel == "PART_OF":
                part_of_edges.append(entry)
        except (KeyError, ValueError):
            continue

    requires_query = """
    UNWIND $batch AS row
    MATCH (src:Skill {id: row.src_id})
    MATCH (dst:Skill {id: row.dst_id})
    MERGE (src)-[r:REQUIRES]->(dst)
    SET r.source = row.source
    """
    for chunk in _batch(requires_edges):
        session.run(requires_query, batch=chunk)

    part_of_query = """
    UNWIND $batch AS row
    MATCH (src:Skill {id: row.src_id})
    MATCH (dst:Skill {id: row.dst_id})
    MERGE (src)-[r:PART_OF]->(dst)
    SET r.source = row.source
    """
    for chunk in _batch(part_of_edges):
        session.run(part_of_query, batch=chunk)
    stats["edges_requires"] = len(requires_edges)
    stats["edges_part_of"] = len(part_of_edges)

    # 5. Universities
    unis = []
    for r in seed.get("universities", []):
        try:
            uid = int(r["id"])
            unis.append({
                "id": uid,
                "name": r.get("name", "").strip(),
                "source": r.get("source", "").strip(),
            })
        except (KeyError, ValueError):
            continue

    uni_query = """
    UNWIND $batch AS row
    MERGE (u:University {id: row.id})
    SET u:KB2, u.name = row.name, u.source = row.source
    """
    for chunk in _batch(unis):
        session.run(uni_query, batch=chunk)
    stats["universities"] = len(unis)

    # 6. University Aliases
    uni_aliases = []
    for r in seed.get("university_aliases", []):
        ak = r.get("alias_key", "").strip()
        try:
            uid = int(r["university_id"])
            if ak:
                uni_aliases.append({
                    "key": ak,
                    "university_id": uid,
                    "source": r.get("source", "").strip(),
                })
        except (KeyError, ValueError):
            continue

    uni_alias_query = """
    UNWIND $batch AS row
    MERGE (ua:UniversityAlias {key: row.key})
    SET ua:KB2, ua.source = row.source
    WITH ua, row
    MATCH (u:University {id: row.university_id})
    MERGE (ua)-[:ALIAS_OF]->(u)
    """
    for chunk in _batch(uni_aliases):
        session.run(uni_alias_query, batch=chunk)
    stats["university_aliases"] = len(uni_aliases)

    # 7. Job Titles
    job_titles = []
    for r in seed.get("job_titles", []):
        try:
            jid = int(r["id"])
            job_titles.append({
                "id": jid,
                "name": r.get("name", "").strip(),
                "alias_key": r.get("alias_key", "").strip(),
                "source": r.get("source", "").strip(),
            })
        except (KeyError, ValueError):
            continue

    jt_query = """
    UNWIND $batch AS row
    MERGE (j:JobTitle {id: row.id})
    SET j:KB2, j.name = row.name, j.alias_key = row.alias_key, j.source = row.source
    """
    for chunk in _batch(job_titles):
        session.run(jt_query, batch=chunk)
    stats["job_titles"] = len(job_titles)

    return stats


def load_kb1_and_merge(
    session: Any,
    books_file: Path,
    seed_dir: Path,
) -> dict[str, int]:
    """Load KB1 from kb1_books.json and merge with KB2 entities."""
    if not books_file.exists():
        return {}

    with books_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    stats: dict[str, int] = {}
    books = data.get("books", [])

    # Build skill lookup for ABOUT relation:
    # Match skill_key(section.title) against skill_key(Skill.name) or Alias.key
    seed = read_seed(seed_dir)
    alias_to_sid: dict[str, int] = {}
    for s in seed.get("skills", []):
        try:
            sid = int(s["id"])
            k = skill_key(s.get("name", ""))
            if k:
                alias_to_sid[k] = sid
        except (KeyError, ValueError):
            continue

    for a in seed.get("skill_aliases", []):
        ak = a.get("alias_key", "").strip()
        try:
            sid = int(a["skill_id"])
            if ak:
                alias_to_sid[ak] = sid
        except (KeyError, ValueError):
            continue

    # 1. Books
    book_rows = []
    section_rows = []
    book_has_section_rows = []
    section_has_section_rows = []
    mentions_rows = []
    about_rows = []

    for b in books:
        bid = b["id"]
        book_rows.append({
            "id": bid,
            "title": b.get("title", ""),
            "authors": b.get("authors", []),
            "edition": str(b.get("edition", "")),
            "licence": b.get("licence", ""),
            "url": b.get("url", ""),
            "sha256": b.get("sha256", ""),
        })

        sections = b.get("sections", [])
        section_ids = {sec["id"] for sec in sections if "id" in sec}

        for sec in sections:
            sec_id = sec["id"]
            sec_title = sec.get("title", "")
            level = int(sec.get("level", 1))
            page = int(sec.get("page", 0))
            source_tag = f"book:{bid}"

            section_rows.append({
                "id": sec_id,
                "title": sec_title,
                "level": level,
                "page": page,
                "source": source_tag,
            })

            # Section tree
            parent_id = sec.get("parent")
            if parent_id and parent_id in section_ids:
                section_has_section_rows.append({
                    "parent_id": parent_id,
                    "section_id": sec_id,
                })
            else:
                book_has_section_rows.append({
                    "book_id": bid,
                    "section_id": sec_id,
                })

            # Mentions: (Section)-[:MENTIONS {count, source}]->(Skill)
            for sname, count in sec.get("mentions", {}).items():
                mentions_rows.append({
                    "section_id": sec_id,
                    "skill_name": sname,
                    "count": int(count),
                    "source": source_tag,
                })

            # About: (Section)-[:ABOUT]->(Skill)
            # Checked when title matches canonical skill or alias key
            k = skill_key(sec_title)
            if k and k in alias_to_sid:
                about_rows.append({
                    "section_id": sec_id,
                    "skill_id": alias_to_sid[k],
                })

    # Execute Book batch
    book_query = """
    UNWIND $batch AS row
    MERGE (b:Book {id: row.id})
    SET b:KB1, b.title = row.title, b.authors = row.authors,
        b.edition = row.edition, b.licence = row.licence,
        b.url = row.url, b.sha256 = row.sha256
    """
    for chunk in _batch(book_rows):
        session.run(book_query, batch=chunk)
    stats["books"] = len(book_rows)

    # Execute Section batch
    section_query = """
    UNWIND $batch AS row
    MERGE (s:Section {id: row.id})
    SET s:KB1, s.title = row.title, s.level = row.level,
        s.page = row.page, s.source = row.source
    """
    for chunk in _batch(section_rows):
        session.run(section_query, batch=chunk)
    stats["sections"] = len(section_rows)

    # HAS_SECTION from Book
    book_has_sec_query = """
    UNWIND $batch AS row
    MATCH (b:Book {id: row.book_id})
    MATCH (s:Section {id: row.section_id})
    MERGE (b)-[:HAS_SECTION]->(s)
    """
    for chunk in _batch(book_has_section_rows):
        session.run(book_has_sec_query, batch=chunk)

    # HAS_SECTION from Section
    sec_has_sec_query = """
    UNWIND $batch AS row
    MATCH (p:Section {id: row.parent_id})
    MATCH (s:Section {id: row.section_id})
    MERGE (p)-[:HAS_SECTION]->(s)
    """
    for chunk in _batch(section_has_section_rows):
        session.run(sec_has_sec_query, batch=chunk)

    # Mentions
    mentions_query = """
    UNWIND $batch AS row
    MATCH (s:Section {id: row.section_id})
    MATCH (sk:Skill {name: row.skill_name})
    MERGE (s)-[m:MENTIONS]->(sk)
    SET m.count = row.count, m.source = row.source
    """
    for chunk in _batch(mentions_rows):
        session.run(mentions_query, batch=chunk)
    stats["mentions"] = len(mentions_rows)

    # About
    about_query = """
    UNWIND $batch AS row
    MATCH (s:Section {id: row.section_id})
    MATCH (sk:Skill {id: row.skill_id})
    MERGE (s)-[:ABOUT]->(sk)
    """
    for chunk in _batch(about_rows):
        session.run(about_query, batch=chunk)
    stats["about"] = len(about_rows)

    # Related from data["related"]:
    # (Skill)-[:RELATED_TO {weight: sections, source: "book:<id>"}]->(Skill)
    related_rows = []
    for item in data.get("related", []):
        src = str(item.get("source") or "")
        source_val = f"book:{src}" if src and not src.startswith("book:") else (src or "book")
        weight = float(item.get("sections") or item.get("weight") or 1.0)
        related_rows.append({
            "a": item["a"],
            "b": item["b"],
            "weight": weight,
            "source": source_val,
        })

    related_query = """
    UNWIND $batch AS row
    MATCH (sa:Skill {name: row.a})
    MATCH (sb:Skill {name: row.b})
    MERGE (sa)-[r:RELATED_TO {source: row.source}]->(sb)
    SET r.weight = row.weight
    """
    for chunk in _batch(related_rows):
        session.run(related_query, batch=chunk)
    stats["related"] = len(related_rows)

    return stats


def get_graph_counts(session: Any) -> dict[str, Any]:
    """Retrieve node counts per label and relationship counts per type."""
    node_labels = [
        "Skill",
        "Category",
        "Alias",
        "University",
        "UniversityAlias",
        "JobTitle",
        "Book",
        "Section",
        "KB1",
        "KB2",
    ]
    node_counts = {}
    for lbl in node_labels:
        res = session.run(f"MATCH (n:{lbl}) RETURN count(n) AS c")
        rec = res.single()
        node_counts[lbl] = rec["c"] if rec else 0

    rel_types = [
        "IN_CATEGORY",
        "ALIAS_OF",
        "REQUIRES",
        "PART_OF",
        "HAS_SECTION",
        "MENTIONS",
        "RELATED_TO",
        "ABOUT",
    ]
    rel_counts = {}
    for rtype in rel_types:
        res = session.run(f"MATCH ()-[r:{rtype}]->() RETURN count(r) AS c")
        rec = res.single()
        rel_counts[rtype] = rec["c"] if rec else 0

    return {"nodes": node_counts, "relationships": rel_counts}


def load_to_neo4j(
    uri: str,
    user: str,
    password: str,
    seed_dir: Path,
    books_file: Path | None = None,
    reset: bool = False,
) -> dict[str, Any]:
    """Connect to Neo4j, apply constraints, load KB2 and KB1, and return graph counts."""
    from neo4j import GraphDatabase

    auth = (user, password) if (user or password) else None
    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session() as session:
            if reset:
                reset_database(session)

            create_constraints(session)
            load_kb2(session, seed_dir)

            if books_file and books_file.exists():
                load_kb1_and_merge(session, books_file, seed_dir)

            return get_graph_counts(session)
    finally:
        driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load KB1 (books) and KB2 (seed CSVs) into Neo4j Knowledge Graph."
    )
    parser.add_argument(
        "--uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j Bolt URI (default: bolt://localhost:7687)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("NEO4J_USER", "neo4j"),
        help="Neo4j username (default: neo4j)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Neo4j password",
    )
    parser.add_argument(
        "--password-env",
        default="NEO4J_PASSWORD",
        help="Environment variable name for Neo4j password (default: NEO4J_PASSWORD)",
    )
    parser.add_argument(
        "--seed",
        default="kb/seed",
        help="Path to seed CSV directory (default: kb/seed)",
    )
    parser.add_argument(
        "--books",
        default="kb/sources/kb1_books.json",
        help="Path to kb1_books.json (default: kb/sources/kb1_books.json)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe the graph database before loading",
    )

    args = parser.parse_args()

    password = args.password
    if password is None:
        password = os.environ.get(args.password_env, "")

    seed_path = Path(args.seed)
    if not seed_path.exists():
        fallback = _AI_SERVICE_DIR / "kb" / "seed"
        if fallback.exists():
            seed_path = fallback

    books_path = Path(args.books)
    if not books_path.exists():
        fallback_books = _AI_SERVICE_DIR / "kb" / "sources" / "kb1_books.json"
        if fallback_books.exists():
            books_path = fallback_books

    try:
        counts = load_to_neo4j(
            uri=args.uri,
            user=args.user,
            password=password,
            seed_dir=seed_path,
            books_file=books_path if books_path.exists() else None,
            reset=args.reset,
        )
        print(json.dumps(counts, indent=2))
    except Exception as e:
        sys.stderr.write(f"Error loading graph to Neo4j: {type(e).__name__}: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
