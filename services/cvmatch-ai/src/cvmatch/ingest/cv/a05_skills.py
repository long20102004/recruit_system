"""A5. Nhan dien ky nang va gan ma (thiet ke 04 A5).

Muc bang chung `ev` theo noi ky nang xuat hien (lay MAX neu nhieu noi):
    description cua kinh nghiem / du an            -> ev.in_description  (1,0)
    technologies cua kinh nghiem / du an           -> ev.in_technologies (0,8)
    skills, summary, certificates                  -> ev.listed_only     (0,6)
Moi ky nang luu: `source_field` (noi cho ev cao nhat, xuat hien dau tien), `evidence_snippet`,
`bullet_ref` (gach chua bang chung, neu co), `last_used` (thang ket thuc muc gan nhat co ky nang).
Phan tu cua `skills` / `technologies` khong khop alias nao -> `unknown_skills`.
"""

from __future__ import annotations

import re

from cvmatch.core.text.normalize import normalize
from cvmatch.ingest.cv.a07_bullets import SECTIONS, split_description
from cvmatch.ingest.cv.record import CvContext, CvRecord, SkillFound, UnknownSkill

_UNKNOWN_MAX_WORDS = 4
_UNKNOWN_MAX_CHARS = 40


def _looks_like_skill_name(s: str) -> bool:
    return 0 < len(s) <= _UNKNOWN_MAX_CHARS and len(re.findall(r"\w+", s)) <= _UNKNOWN_MAX_WORDS


class _Collector:
    def __init__(self) -> None:
        self.best: dict[str, SkillFound] = {}
        self.last_used: dict[str, str] = {}
        self.unknown: dict[str, UnknownSkill] = {}

    def add(self, sid: str, ev: float, source: str, snippet: str | None,
            ref: tuple[str, int, int] | None = None) -> None:
        cur = self.best.get(sid)
        if cur is None or ev > cur.ev:  # bang nhau -> giu noi xuat hien truoc
            self.best[sid] = SkillFound(skill_id=sid, ev=ev, source_field=source,
                                        evidence_snippet=snippet, bullet_ref=ref)

    def used(self, sid: str, end_ym: str | None) -> None:
        if end_ym and end_ym > self.last_used.get(sid, ""):
            self.last_used[sid] = end_ym

    def unknown_item(self, item_norm: str, example: str) -> None:
        if _looks_like_skill_name(item_norm) and item_norm not in self.unknown:
            self.unknown[item_norm] = UnknownSkill(text=item_norm, example=example)


def step_a05(rec: CvRecord, ctx: CvContext) -> CvRecord:
    ev = ctx.cfg.prep.ev
    m = ctx.matcher
    cv = rec.anon_json or {}
    cv_raw = rec.anon_raw or {}
    col = _Collector()
    min_words = ctx.cfg.prep.bullet.min_words

    # 1) description + technologies cua kinh nghiem / du an
    for section, key in SECTIONS:
        items, items_raw = cv.get(key) or [], cv_raw.get(key) or []
        recency = {src: idx for idx, src in enumerate(rec.item_order.get(section, []))}
        for src, item in enumerate(items):
            end_ym = item.get("end")
            for part in split_description(items_raw[src].get("description"), min_words):
                text = normalize(part.raw)
                ref = (section, recency[src], part.pos) if part.kept else None
                for sid in m.find_ids(text):
                    col.add(sid, ev.in_description, f"{key}[{src}].{part.path}", text, ref)
                    col.used(sid, end_ym)
            for k, tech in enumerate(item.get("technologies") or []):
                if not isinstance(tech, str):
                    continue
                matches = m.match_list_item(tech)
                if not matches:
                    col.unknown_item(normalize(tech).strip(" ,;."), f"{key}[{src}].technologies: {tech}")
                for mt in matches:
                    col.add(mt.skill_id, ev.in_technologies, f"{key}[{src}].technologies[{k}]",
                            normalize(tech))
                    col.used(mt.skill_id, end_ym)

    # 2) chi liet ke: skills, summary, certificates
    for k, s in enumerate(cv.get("skills") or []):
        if not isinstance(s, str):
            continue
        matches = m.match_list_item(s)
        if not matches:
            col.unknown_item(normalize(s).strip(" ,;."), f"skills[{k}]: {s}")
        for mt in matches:
            col.add(mt.skill_id, ev.listed_only, f"skills[{k}]", normalize(s))
    summary = cv.get("summary")
    if isinstance(summary, str):
        for sid in m.find_ids(summary):
            col.add(sid, ev.listed_only, "summary", summary)
    for k, c in enumerate(cv.get("certificates") or []):
        text = c if isinstance(c, str) else " ".join(str(v) for v in (c or {}).values() if isinstance(v, str))
        for sid in m.find_ids(normalize(text)):
            col.add(sid, ev.listed_only, f"certificates[{k}]", normalize(text))

    found = []
    for sid, sf in col.best.items():
        sf.last_used = col.last_used.get(sid)
        found.append(sf)
    found.sort(key=lambda x: (-x.ev, x.skill_id))
    rec.skills_found = found
    rec.unknown_skills = list(col.unknown.values())
    return rec
