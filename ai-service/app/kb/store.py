"""In-memory KnowledgeBase holding skill linker, graph edges, and school aliases."""

from __future__ import annotations

import re

import csv
from dataclasses import dataclass
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
        )


def load_kb(dsn: str | None, seed_dir: str | Path) -> KnowledgeBase | None:
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
