"""In-memory KnowledgeBase holding skill linker, graph edges, and school aliases."""

from __future__ import annotations

import re

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import logger
from app.kb.keys import school_key
from app.kb.linker import SkillLinker

__all__ = ["KnowledgeBase", "load_kb", "kb_state", "kb_summary"]


@dataclass
class KnowledgeBase:
    source: str
    linker: SkillLinker
    skills: dict[int, tuple[str, str]]
    edges: dict[int, list[tuple[str, int]]]
    school_alias: dict[str, int]
    universities: dict[int, str]
    related: dict[int, list[tuple[int, float]]] = field(default_factory=dict)

    def link_school(self, raw: str | None) -> tuple[int, str] | None:
        """Resolve a raw school name to canonical (university_id, university_name)."""
        if not raw or not isinstance(raw, str) or not raw.strip():
            return None
        # Full string first, then without "(...)" (e.g. "Học viện ... (PTIT)"),
        # then each parenthesised part on its own (the abbreviation).
        # Same for a " - " suffix ("Posts and Telecommunications Institute of Technology - PTIT").
        outside = re.sub(r"\([^)]*\)", " ", raw)
        inside = re.findall(r"\(([^)]*)\)", raw)
        # Only the first part, plus the last part when it is a single-token abbreviation:
        # "... - ĐHQG TP.HCM" names the parent university and must not be linked.
        parts = [p.strip() for p in re.split(r"\s+[-–—]\s+", outside) if p.strip()]
        dashed = []
        if len(parts) > 1:
            dashed = [parts[0]] + ([parts[-1]] if len(parts[-1].split()) == 1 else [])
        for candidate in [raw, outside, *inside, *dashed]:
            k = school_key(candidate)
            uid = self.school_alias.get(k) if k else None
            if uid is not None and uid in self.universities:
                return (uid, self.universities[uid])
        return None

    @classmethod
    def from_csv(cls, seed_dir: str | Path) -> KnowledgeBase:
        """Read named columns; public-source provenance columns are metadata only."""
        seed_path = Path(seed_dir)
        if not seed_path.exists() or not seed_path.is_dir():
            raise FileNotFoundError(f"Seed directory not found: {seed_path}")

        skills_csv = seed_path / "skills.csv"
        if not skills_csv.exists():
            raise FileNotFoundError(f"Required seed file missing: {skills_csv}")

        linker = SkillLinker.from_csv(seed_path)
        skills: dict[int, tuple[str, str]] = {}
        edges: dict[int, list[tuple[str, int]]] = {}
        school_alias: dict[str, int] = {}
        universities: dict[int, str] = {}

        with skills_csv.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = int(row["id"])
                name = row["name"].strip()
                category = row.get("category", "").strip()
                skills[sid] = (name, category)

        edges_csv = seed_path / "skill_edges.csv"
        if edges_csv.exists():
            with edges_csv.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    src_id = int(row["src_id"])
                    rel = row["rel"].strip()
                    dst_id = int(row["dst_id"])
                    if src_id not in edges:
                        edges[src_id] = []
                    edges[src_id].append((rel, dst_id))

            for src in edges:
                edges[src].sort(key=lambda x: (x[0], x[1]))

        unis_csv = seed_path / "universities.csv"
        if unis_csv.exists():
            with unis_csv.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = int(row["id"])
                    name = row["name"].strip()
                    universities[uid] = name

        uni_alias_csv = seed_path / "university_aliases.csv"
        if uni_alias_csv.exists():
            with uni_alias_csv.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ak = row.get("alias_key", "").strip()
                    uid = int(row["university_id"])
                    if ak:
                        school_alias[ak] = uid

        for uid, name in universities.items():
            k = school_key(name)
            if k and k not in school_alias:
                school_alias[k] = uid

        return cls(
            source="csv",
            linker=linker,
            skills=skills,
            edges=edges,
            school_alias=school_alias,
            universities=universities,
            related=_related_from_books(Path(seed_dir).parent / "sources" / "kb1_books.json", skills),
        )

    @classmethod
    def from_db(cls, dsn: str) -> KnowledgeBase:
        import psycopg

        linker = SkillLinker.from_db(dsn)
        skills: dict[int, tuple[str, str]] = {}
        edges: dict[int, list[tuple[str, int]]] = {}
        school_alias: dict[str, int] = {}
        universities: dict[int, str] = {}

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT s.id, s.name, c.name FROM skill s JOIN category c ON c.id=s.category_id ORDER BY s.id"
                )
                for sid, sname, cname in cur.fetchall():
                    skills[int(sid)] = (str(sname).strip(), str(cname).strip())

                cur.execute(
                    "SELECT src_id, rel, dst_id FROM skill_edge ORDER BY src_id, rel, dst_id"
                )
                for src_id, rel, dst_id in cur.fetchall():
                    src = int(src_id)
                    r = str(rel).strip()
                    dst = int(dst_id)
                    if src not in edges:
                        edges[src] = []
                    edges[src].append((r, dst))

                cur.execute("SELECT id, name FROM university ORDER BY id")
                for uid, uname in cur.fetchall():
                    universities[int(uid)] = str(uname).strip()

                cur.execute("SELECT alias_key, university_id FROM university_alias")
                for ak, uid in cur.fetchall():
                    ak_clean = str(ak).strip()
                    if ak_clean:
                        school_alias[ak_clean] = int(uid)

        for src in edges:
            edges[src].sort(key=lambda x: (x[0], x[1]))

        for uid, name in universities.items():
            k = school_key(name)
            if k and k not in school_alias:
                school_alias[k] = uid

        return cls(
            source="postgres",
            linker=linker,
            skills=skills,
            edges=edges,
            school_alias=school_alias,
            universities=universities,
            related={},
        )

    @classmethod
    def from_neo4j(
        cls,
        uri: str,
        user: str = "neo4j",
        password: str = "",
    ) -> KnowledgeBase:
        from neo4j import GraphDatabase

        skills: dict[int, tuple[str, str]] = {}
        edges: dict[int, list[tuple[str, int]]] = {}
        school_alias: dict[str, int] = {}
        universities: dict[int, str] = {}
        aliases: dict[str, int] = {}
        surfaces: dict[str, int] = {}
        related: dict[int, list[tuple[int, float]]] = {}

        auth = (user, password) if (user or password) else None
        driver = GraphDatabase.driver(uri, auth=auth)
        try:
            with driver.session() as session:
                # 1. Skills
                res = session.run(
                    "MATCH (s:Skill) RETURN s.id AS id, s.name AS name, s.category AS category ORDER BY s.id"
                )
                for rec in res:
                    sid = int(rec["id"])
                    name = str(rec["name"]).strip()
                    cat = str(rec.get("category") or "").strip()
                    skills[sid] = (name, cat)

                # 2. Aliases
                res = session.run(
                    "MATCH (a:Alias)-[:ALIAS_OF]->(s:Skill) "
                    "RETURN a.key AS key, a.surface AS surface, s.id AS skill_id"
                )
                for rec in res:
                    k = str(rec["key"]).strip()
                    sid = int(rec["skill_id"])
                    surf = str(rec.get("surface") or "").strip()
                    if k:
                        aliases[k] = sid
                    if surf:
                        surfaces[surf.casefold().strip()] = sid

                # 3. Skill edges
                res = session.run(
                    "MATCH (src:Skill)-[r:REQUIRES|PART_OF]->(dst:Skill) "
                    "RETURN src.id AS src_id, type(r) AS rel, dst.id AS dst_id "
                    "ORDER BY src_id, rel, dst_id"
                )
                for rec in res:
                    src_id = int(rec["src_id"])
                    rel = str(rec["rel"]).strip()
                    dst_id = int(rec["dst_id"])
                    if src_id not in edges:
                        edges[src_id] = []
                    edges[src_id].append((rel, dst_id))

                for src in edges:
                    edges[src].sort(key=lambda x: (x[0], x[1]))

                # 4. Related
                res = session.run(
                    "MATCH (a:Skill)-[r:RELATED_TO]-(b:Skill) "
                    "RETURN a.id AS a_id, b.id AS b_id, r.weight AS weight"
                )
                related_map: dict[int, dict[int, float]] = {}
                for rec in res:
                    a_id = int(rec["a_id"])
                    b_id = int(rec["b_id"])
                    w = float(rec["weight"]) if rec.get("weight") is not None else 1.0
                    if a_id not in related_map:
                        related_map[a_id] = {}
                    if b_id not in related_map[a_id] or w > related_map[a_id][b_id]:
                        related_map[a_id][b_id] = w
                    if b_id not in related_map:
                        related_map[b_id] = {}
                    if a_id not in related_map[b_id] or w > related_map[b_id][a_id]:
                        related_map[b_id][a_id] = w

                for sid, targets in related_map.items():
                    related[sid] = sorted(targets.items(), key=lambda x: (-x[1], x[0]))

                # 5. Universities
                res = session.run(
                    "MATCH (u:University) RETURN u.id AS id, u.name AS name ORDER BY u.id"
                )
                for rec in res:
                    uid = int(rec["id"])
                    name = str(rec["name"]).strip()
                    universities[uid] = name

                # 6. University aliases
                res = session.run(
                    "MATCH (ua:UniversityAlias)-[:ALIAS_OF]->(u:University) "
                    "RETURN ua.key AS key, u.id AS university_id"
                )
                for rec in res:
                    ak = str(rec["key"]).strip()
                    uid = int(rec["university_id"])
                    if ak:
                        school_alias[ak] = uid
        finally:
            driver.close()

        for uid, name in universities.items():
            k = school_key(name)
            if k and k not in school_alias:
                school_alias[k] = uid

        linker = SkillLinker(skills=skills, aliases=aliases, surfaces=surfaces)

        return cls(
            source="neo4j",
            linker=linker,
            skills=skills,
            edges=edges,
            school_alias=school_alias,
            universities=universities,
            related=related,
        )


def _related_from_books(path: Path, skills: dict[int, tuple[str, str]]) -> dict[int, list[tuple[int, float]]]:
    """RELATED_TO from the KB1 snapshot (books) when the KB is read from CSV (no Neo4j)."""
    if not path.exists():
        return {}
    import json

    by_name = {name: sid for sid, (name, _) in skills.items()}
    best: dict[int, dict[int, float]] = {}
    for rel in json.loads(path.read_text(encoding="utf-8")).get("related", []):
        a, b = by_name.get(rel.get("a")), by_name.get(rel.get("b"))
        if a is None or b is None or a == b:
            continue
        w = float(rel.get("sections") or 1)
        for x, y in ((a, b), (b, a)):
            if w > best.setdefault(x, {}).get(y, 0.0):
                best[x][y] = w
    return {sid: sorted(t.items(), key=lambda kv: (-kv[1], kv[0])) for sid, t in best.items()}


def load_kb(
    dsn: str | None,
    seed_dir: str | Path,
    neo4j_uri: str | None = None,
    neo4j_user: str | None = None,
    neo4j_password: str | None = None,
) -> KnowledgeBase | None:
    if neo4j_uri:
        try:
            kb = KnowledgeBase.from_neo4j(
                uri=neo4j_uri,
                user=neo4j_user or "neo4j",
                password=neo4j_password or "",
            )
            logger.info(
                "KB loaded from neo4j: %d skills, %d universities",
                len(kb.skills),
                len(kb.universities),
            )
            return kb
        except Exception as e:
            logger.warning(
                "KB neo4j unavailable (%s), falling back",
                type(e).__name__,
            )

    if dsn:
        try:
            kb = KnowledgeBase.from_db(dsn)
            logger.info(
                "KB loaded from postgres: %d skills, %d universities",
                len(kb.skills),
                len(kb.universities),
            )
            return kb
        except Exception as e:
            logger.warning(
                "KB postgres unavailable (%s), falling back to seed CSV",
                type(e).__name__,
            )

    try:
        kb = KnowledgeBase.from_csv(seed_dir)
        logger.info(
            "KB loaded from csv: %d skills, %d universities",
            len(kb.skills),
            len(kb.universities),
        )
        return kb
    except Exception as e:
        logger.error("KB load failed (%s)", type(e).__name__)
        return None


kb_state: dict[str, KnowledgeBase | None] = {"kb": None}


def kb_summary(kb: KnowledgeBase | None) -> dict[str, Any] | None:
    if kb is None:
        return None
    return {
        "source": kb.source,
        "skills": len(kb.skills),
        "universities": len(kb.universities),
    }
