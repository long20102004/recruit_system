"""Ban chup KB (thiet ke 02 muc 8). Tien xu ly KHONG hoi Neo4j; doc ban chup nay.

Dinh dang thu muc snapshot (T01 xuat, `cvmatch kb import` nap vao Postgres):

    <thu muc>/manifest.json            {"ontology_version", "created_at", "include_candidate", "files": {...}}
    <thu muc>/skill_ontology.jsonl     {skill_id, name, aliases[], type, parents[], categories_sibling_ok[], status}
    <thu muc>/role_title_map.jsonl     {kind: "title", alias, role_group} | {kind: "level", alias, level_rank}
    <thu muc>/role_distance.jsonl      {group_a, group_b, m, method}
    <thu muc>/major_group.jsonl        {major_alias, group}
    <thu muc>/ambiguous_aliases.jsonl  {alias, candidates[]}

Moi alias duoc chuan hoa LAI bang `core.text.normalize` khi nap, de chac chan cung ham voi CV/JD.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from cvmatch.core.text.normalize import normalize

SNAPSHOT_FILES = ("skill_ontology", "role_title_map", "role_distance", "major_group", "ambiguous_aliases")


@dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    aliases: tuple[str, ...]
    type: Literal["technology", "concept"]
    parents: tuple[str, ...] = ()
    categories_sibling_ok: tuple[str, ...] = ()
    status: str = "accepted"


@dataclass
class KBSnapshot:
    ontology_version: str
    skills: dict[str, Skill]
    title_map: dict[str, str]                     # alias chuc danh -> role_group
    level_map: dict[str, int]                     # alias cap bac -> level_rank
    role_distance: dict[tuple[str, str, str], float]  # (group_a, group_b, method) -> m
    major_map: dict[str, str]                     # alias nganh -> it | related | other
    ambiguous: dict[str, tuple[str, ...]]         # alias de nham -> skill_id co the
    manifest: dict = field(default_factory=dict)

    # ----------------------------------------------------------------- tien ich

    def alias_map(self) -> dict[str, str]:
        """alias (da chuan hoa) -> skill_id. Ten chuan cung la mot alias.

        Quy tac KB 4.1: moi alias thuoc dung mot ky nang; vi pham -> ValueError.
        """
        out: dict[str, str] = {}
        for s in self.skills.values():
            for a in {normalize(s.name), *s.aliases}:
                if not a:
                    continue
                prev = out.get(a)
                if prev is not None and prev != s.skill_id:
                    raise ValueError(f"alias '{a}' tro toi hai ky nang: {prev}, {s.skill_id}")
                out[a] = s.skill_id
        return out

    def role_groups(self) -> set[str]:
        return set(self.title_map.values())

    # ----------------------------------------------------------------- nap

    @classmethod
    def from_dir(cls, path: str | Path) -> "KBSnapshot":
        p = Path(path)
        manifest = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        rows = {name: _read_jsonl(p / f"{name}.jsonl") for name in SNAPSHOT_FILES}
        return cls.from_rows(manifest, rows)

    @classmethod
    def from_rows(cls, manifest: dict, rows: dict[str, list[dict]]) -> "KBSnapshot":
        skills: dict[str, Skill] = {}
        for r in rows["skill_ontology"]:
            skills[r["skill_id"]] = Skill(
                skill_id=r["skill_id"],
                name=r["name"],
                aliases=tuple(dict.fromkeys(normalize(a) for a in r.get("aliases", []) if a)),
                type=r["type"],
                parents=tuple(r.get("parents") or ()),
                categories_sibling_ok=tuple(r.get("categories_sibling_ok") or ()),
                status=r.get("status", "accepted"),
            )
        title_map: dict[str, str] = {}
        level_map: dict[str, int] = {}
        for r in rows["role_title_map"]:
            if r["kind"] == "title":
                title_map[normalize(r["alias"])] = r["role_group"]
            else:
                level_map[normalize(r["alias"])] = int(r["level_rank"])
        dist = {(r["group_a"], r["group_b"], r["method"]): float(r["m"]) for r in rows["role_distance"]}
        majors = {normalize(r["major_alias"]): r["group"] for r in rows["major_group"]}
        amb = {normalize(r["alias"]): tuple(r.get("candidates") or ()) for r in rows["ambiguous_aliases"]}
        snap = cls(
            ontology_version=manifest["ontology_version"],
            skills=skills,
            title_map=title_map,
            level_map=level_map,
            role_distance=dist,
            major_map=majors,
            ambiguous=amb,
            manifest=manifest,
        )
        snap.alias_map()  # kiem alias trung ngay khi nap (03: "dung, khong nap KB do")
        return snap


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
