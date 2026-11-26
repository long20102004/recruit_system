"""B4. Gan ma ky nang JD (thiet ke 05 B4).

- Phan tu `skills` -> skill_id (cung quy tac khop A5); giu `required`; `importance` -> `w_imp`
  (core 1,0 / medium 0,7 / minor 0,4; thieu -> 1,0).
- Do them `requirements` de bat ky nang Module 1 bo sot -> `required = false`, `w_imp = minor`,
  `source = requirements`.
- Nhom "A hoac B" ("Java hoặc Kotlin", "MySQL/PostgreSQL"): cac ky nang chung `group_id`.
- Khong khop alias nao -> unknown_skill (chu goc van nam trong query_text cho BM25 / dense).
"""

from __future__ import annotations

import re

from cvmatch.core.kb.matcher import Match
from cvmatch.core.text.normalize import normalize
from cvmatch.ingest.jd.prepare import skill_name
from cvmatch.ingest.jd.record import JdRecord, JdSkill, PrepContext

# Chi co cac tu noi nay giua hai ky nang lien tiep -> nhom "A hoac B"
_OR_GAP_RE = re.compile(r"^\s*(?:/|\||hoặc|hay|or|hoặc là)\s*$")


def or_groups(text: str, matches: list[Match]) -> list[list[str]]:
    """Gom cac ky nang dung canh nhau, ngan cach boi '/', 'hoặc', 'or' thanh nhom."""
    groups: list[list[str]] = []
    cur: list[str] = []
    for a, b in zip(matches, matches[1:]):
        if _OR_GAP_RE.match(text[a.end:b.start]):
            if not cur:
                cur = [a.skill_id]
            cur.append(b.skill_id)
        elif cur:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return [list(dict.fromkeys(g)) for g in groups if len(set(g)) > 1]


def w_imp_of(importance: str | None, ctx: PrepContext) -> float:
    w = ctx.cfg.prep.w_imp
    return {"core": w.core, "medium": w.medium, "minor": w.minor}.get(normalize(importance or ""), w.default)


def step_b04(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    m = ctx.matcher
    found: dict[str, JdSkill] = {}
    group_of: dict[str, int] = {}
    next_group = 1

    def assign_groups(groups: list[list[str]]) -> None:
        nonlocal next_group
        for g in groups:
            gid = next((group_of[s] for s in g if s in group_of), None) or next_group
            if gid == next_group:
                next_group += 1
            for s in g:
                group_of.setdefault(s, gid)

    raw_skills = rec.raw_json.get("skills") or []
    rec.n_skill_items = len(raw_skills)
    for s in raw_skills:
        name = skill_name(s)
        required = s.get("required", True) if isinstance(s, dict) else True
        w = w_imp_of(s.get("importance") if isinstance(s, dict) else None, ctx)
        matches = m.match_list_item(name)
        if not matches:
            rec.unknown_skills.append((normalize(name).strip(" ,;."), f"jd skills: {name}"))
            continue
        assign_groups(or_groups(normalize(name), matches))
        for mt in matches:
            cur = found.get(mt.skill_id)
            if cur is None:
                found[mt.skill_id] = JdSkill(skill_id=mt.skill_id, required=bool(required), w_imp=w,
                                             source="module1", raw_text=name)
            else:  # trung trong skills -> lay muc cao hon
                cur.required = cur.required or bool(required)
                cur.w_imp = max(cur.w_imp, w)

    for line in rec.raw_json.get("requirements") or []:
        text = normalize(line)
        matches = m.find(text)
        assign_groups(or_groups(text, matches))
        for mt in matches:
            if mt.skill_id not in found:
                found[mt.skill_id] = JdSkill(skill_id=mt.skill_id, required=False,
                                             w_imp=ctx.cfg.prep.w_imp.minor, source="requirements",
                                             raw_text=line)

    for sid, js in found.items():
        js.group_id = group_of.get(sid)
    rec.skills_found = list(found.values())
    rec.unknown_skills = list(dict(rec.unknown_skills).items())  # bo trung, giu thu tu
    return rec
