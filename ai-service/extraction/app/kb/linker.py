"""In-memory skill entity linker backed by CSV seed or PostgreSQL KB."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from rapidfuzz import fuzz, process

from app.kb.keys import skill_key
from app.postprocess.skills import clean_skill_list
from app.postprocess.text_match import normalize

__all__ = ["Link", "SkillLinker"]


@dataclass(frozen=True)
class Link:
    raw: str
    skill_id: int | None
    name: str | None
    category: str | None
    method: str
    score: float


class SkillLinker:
    """In-memory skill linker resolving raw skill mentions to canonical entities."""

    _SPLIT_REGEX = re.compile(r"\s*/\s*|\s+&\s+|\s+and\s+|\s*[(),]\s*")
    _JOIN_REGEX = re.compile(r"\s*\+\s*|(?<=[A-Za-z0-9.])-(?=[A-Za-z])")
    _VERSION = re.compile(r"[\s-]*v?\d+(?:\.(?:\d+|x))*\+?$", re.IGNORECASE)
    _GENERIC_TAIL = re.compile(r"\s+(?:core|authentication|framework|library|basics?|cơ bản|programming)$", re.IGNORECASE)

    @classmethod
    def _variant_text(cls, text: str) -> str:
        """"ASP.NET MVC Core 6.x" -> "ASP.NET MVC", "JavaScript(ES6+)" -> "JavaScript", "Java Core" -> "Java"."""
        v = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip()
        for _ in range(3):
            v2 = cls._GENERIC_TAIL.sub("", cls._VERSION.sub("", v)).strip(" -")
            if v2 == v:
                break
            v = v2
        return v

    def __init__(
        self,
        skills: dict[int, tuple[str, str]],
        aliases: dict[str, int],
        surfaces: dict[str, int],
    ) -> None:
        self.skills: dict[int, tuple[str, str]] = dict(skills)
        self.aliases: dict[str, int] = dict(aliases)
        self.surfaces: dict[str, int] = {
            s.casefold().strip(): sid for s, sid in surfaces.items() if s and s.strip()
        }

        # Thêm tự động: mỗi skill name -> surfaces[name.casefold()] và aliases[skill_key(name)] nếu chưa có
        for sid, (name, _) in self.skills.items():
            name_norm = name.casefold().strip()
            if name_norm and name_norm not in self.surfaces:
                self.surfaces[name_norm] = sid
            k = skill_key(name)
            if k and k not in self.aliases:
                self.aliases[k] = sid

        # Lưu list key cho fuzzy
        self._keys: list[str] = sorted(self.aliases.keys())
        # Linguistic normalization, not new KB facts: Vietnamese soft-skill
        # names may omit the connective "theo" or nominal "chủ nghĩa" prefix.
        # Restrict to source-backed Soft Skill surfaces and unique owners.
        soft_candidates: dict[str, set[int]] = {}
        for surface, sid in self.surfaces.items():
            if self.skills[sid][1] != "Soft Skill":
                continue
            text = normalize(surface)
            reduced = re.sub(r"^chu nghia\s+", "", text)
            reduced = re.sub(r"\btheo\b", " ", reduced)
            if reduced != text:
                soft_candidates.setdefault(skill_key(reduced), set()).add(sid)
        self._soft_variants = {k: next(iter(ids)) for k, ids in soft_candidates.items()
                               if k and len(ids) == 1 and (k not in self.aliases or self.aliases[k] in ids)}

    @classmethod
    def from_csv(cls, seed_dir: str | Path) -> SkillLinker:
        """Load named columns, tolerating source/source_id provenance metadata.

        Explicit DB projections below likewise do not depend on table column order.
        """
        seed_path = Path(seed_dir)
        skills: dict[int, tuple[str, str]] = {}
        aliases: dict[str, int] = {}
        surfaces: dict[str, int] = {}

        skills_csv = seed_path / "skills.csv"
        if skills_csv.exists():
            with skills_csv.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sid = int(row["id"])
                    name = row["name"].strip()
                    category = row.get("category", "").strip()
                    skills[sid] = (name, category)

        aliases_csv = seed_path / "skill_aliases.csv"
        if aliases_csv.exists():
            with aliases_csv.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    alias_key = row["alias_key"].strip()
                    sid = int(row["skill_id"])
                    surface = row.get("surface", "").strip()
                    if alias_key:
                        aliases[alias_key] = sid
                    if surface:
                        surfaces[surface.casefold().strip()] = sid

        return cls(skills=skills, aliases=aliases, surfaces=surfaces)

    @classmethod
    def from_db(cls, dsn: str) -> SkillLinker:
        """Load skills and aliases from PostgreSQL database."""
        import psycopg

        skills: dict[int, tuple[str, str]] = {}
        aliases: dict[str, int] = {}
        surfaces: dict[str, int] = {}

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT s.id, s.name, c.name FROM skill s JOIN category c ON c.id=s.category_id"
                )
                for sid, sname, cname in cur.fetchall():
                    skills[int(sid)] = (str(sname).strip(), str(cname).strip())

                cur.execute("SELECT alias_key, skill_id, surface FROM skill_alias")
                for alias_key, skill_id, surface in cur.fetchall():
                    ak = str(alias_key).strip()
                    sid = int(skill_id)
                    surf = str(surface).strip() if surface else ""
                    if ak:
                        aliases[ak] = sid
                    if surf:
                        surfaces[surf.casefold().strip()] = sid

        return cls(skills=skills, aliases=aliases, surfaces=surfaces)

    def _link_atomic(self, text: str) -> Link | None:
        """Attempt exact, normalized, or fuzzy matching on a single atomic part (no split)."""
        stripped = text.strip()
        if not stripped:
            return None

        # 1. Exact
        surface_key = stripped.casefold()
        if surface_key in self.surfaces:
            sid = self.surfaces[surface_key]
            name, category = self.skills[sid]
            return Link(
                raw=stripped,
                skill_id=sid,
                name=name,
                category=category,
                method="exact",
                score=100.0,
            )

        # 2. Normalized
        key = skill_key(stripped)
        if key and key in self.aliases:
            sid = self.aliases[key]
            name, category = self.skills[sid]
            return Link(
                raw=stripped,
                skill_id=sid,
                name=name,
                category=category,
                method="normalized",
                score=100.0,
            )

        if key in self._soft_variants:
            sid = self._soft_variants[key]
            name, category = self.skills[sid]
            return Link(raw=stripped, skill_id=sid, name=name, category=category,
                        method="normalized", score=100.0)

        # 3. Fuzzy (key length >= 4)
        if key and len(key) >= 4 and self._keys:
            match = process.extractOne(
                key, self._keys, scorer=fuzz.ratio, score_cutoff=90
            )
            if match is not None and self.skills[self.aliases[match[0]]][1] == "Soft Skill":
                match = None  # soft skills link only exactly: fuzzy hits technical words ("Delegates")
            if match is not None:
                matched_key, score, _ = match
                sid = self.aliases[matched_key]
                name, category = self.skills[sid]
                return Link(
                    raw=stripped,
                    skill_id=sid,
                    name=name,
                    category=category,
                    method="fuzzy",
                    score=float(score),
                )

        return None

    def _link_one(self, piece: str) -> list[Link]:
        """Link a single cleaned piece according to exact -> normalized -> split -> fuzzy -> unlinked."""
        stripped = piece.strip()
        if not stripped:
            return []

        # 1. Exact
        surface_key = stripped.casefold()
        if surface_key in self.surfaces:
            sid = self.surfaces[surface_key]
            name, category = self.skills[sid]
            return [
                Link(
                    raw=stripped,
                    skill_id=sid,
                    name=name,
                    category=category,
                    method="exact",
                    score=100.0,
                )
            ]

        # 2. Normalized
        key = skill_key(stripped)
        if key and key in self.aliases:
            sid = self.aliases[key]
            name, category = self.skills[sid]
            return [
                Link(
                    raw=stripped,
                    skill_id=sid,
                    name=name,
                    category=category,
                    method="normalized",
                    score=100.0,
                )
            ]

        if key in self._soft_variants:
            sid = self._soft_variants[key]
            name, category = self.skills[sid]
            return [Link(raw=stripped, skill_id=sid, name=name, category=category,
                         method="normalized", score=100.0)]

        # 2b. Spelling variant: drop "(...)", version suffixes, generic trailing words
        variant = self._variant_text(stripped)
        if variant and variant.casefold() != stripped.casefold():
            v = self._link_atomic(variant)
            if v is not None:
                return [Link(raw=stripped, skill_id=v.skill_id, name=v.name, category=v.category,
                             method="variant", score=v.score)]

        # 2c. Joined with "-" or "+" ("Nodejs-Expressjs"): only when every part links
        joined = [p.strip() for p in self._JOIN_REGEX.split(stripped) if p and p.strip()]
        if len(joined) >= 2:
            joined_links = [self._link_atomic(p) for p in joined]
            if all(joined_links):
                return [Link(raw=p, skill_id=l.skill_id, name=l.name, category=l.category, method="split", score=l.score)
                        for p, l in zip(joined, joined_links)]

        # 3. Split: regex r"\s*/\s*|\s+&\s+|\s+and\s+|\s*[(),]\s*"
        parts = [p.strip() for p in self._SPLIT_REGEX.split(stripped) if p and p.strip()]
        if len(parts) >= 2:
            split_links: list[Link] = []
            linked_count = 0
            for part in parts:
                atomic_link = self._link_atomic(part)
                if atomic_link is not None:
                    linked_count += 1
                    split_links.append(
                        Link(
                            raw=part,
                            skill_id=atomic_link.skill_id,
                            name=atomic_link.name,
                            category=atomic_link.category,
                            method="split",
                            score=atomic_link.score,
                        )
                    )
                else:
                    split_links.append(
                        Link(
                            raw=part,
                            skill_id=None,
                            name=None,
                            category=None,
                            method="unlinked",
                            score=0.0,
                        )
                    )
            if linked_count >= 1:
                return split_links

        # 4. Fuzzy: key=skill_key(piece), len(key)>=4
        if key and len(key) >= 4 and self._keys:
            match = process.extractOne(
                key, self._keys, scorer=fuzz.ratio, score_cutoff=90
            )
            if match is not None and self.skills[self.aliases[match[0]]][1] == "Soft Skill":
                match = None  # soft skills link only exactly: fuzzy hits technical words ("Delegates")
            if match is not None:
                matched_key, score, _ = match
                sid = self.aliases[matched_key]
                name, category = self.skills[sid]
                return [
                    Link(
                        raw=stripped,
                        skill_id=sid,
                        name=name,
                        category=category,
                        method="fuzzy",
                        score=float(score),
                    )
                ]

        # 5. Else: unlinked
        return [
            Link(
                raw=stripped,
                skill_id=None,
                name=None,
                category=None,
                method="unlinked",
                score=0.0,
            )
        ]

    def link(self, raw: str) -> list[Link]:
        """Link a raw skill string into KB skill entities."""
        pieces = clean_skill_list([raw]) if raw else []
        if not pieces:
            return []
        results: list[Link] = []
        for piece in pieces:
            results.extend(self._link_one(piece))
        return results

    def link_many(self, raws: Iterable[str]) -> list[Link]:
        """Link multiple raw skill strings, deduping linked skills by skill_id preserving order."""
        seen_ids: set[int] = set()
        results: list[Link] = []
        for raw in raws:
            for item in self.link(raw):
                if item.skill_id is None:
                    results.append(item)
                elif item.skill_id not in seen_ids:
                    seen_ids.add(item.skill_id)
                    results.append(item)
        return results
