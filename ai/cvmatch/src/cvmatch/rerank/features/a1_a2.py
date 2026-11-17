"""A1 (ky nang bat buoc), A2 (ky nang uu tien) qua KB (thiet ke 07 muc 5.5).

    score_req(r) = max_{s thuoc CV, opt thuoc options(r)} rel(s, opt) x ev(s)
    A = sum_r w_imp_r x score_req(r) / sum_r w_imp_r
Nhom "A hoac B" (`jd_skill.group_id`) la MOT yeu cau, w_imp = max trong nhom.

P1 (`a1.use_kb_rel = false`): A1 = `s_skill` cua Retrieve (dung cong thuc tren voi rel in {1, 0}),
A2 = None. `skill_facts` (met / partial / missing) luon tinh de Explain dung.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cvmatch.core.contracts import SkillFacts, SkillMet, SkillPartial


@dataclass(frozen=True)
class JdSkill:
    skill_id: str
    required: bool
    w_imp: float
    group_id: int | None = None


@dataclass(frozen=True)
class CvSkill:
    skill_id: str
    ev: float
    bullet_id: int | None = None
    source_field: str = ""

    @property
    def evidence_id(self) -> str:
        return str(self.bullet_id) if self.bullet_id is not None else self.source_field


def requirements(jd_skills: list[JdSkill], required: bool) -> list[tuple[float, list[str]]]:
    """-> [(w_imp, [skill_id cac lua chon])] theo thu tu xuat hien."""
    reqs: dict[object, tuple[float, list[str]]] = {}
    for s in jd_skills:
        if s.required != required:
            continue
        key = ("g", s.group_id) if s.group_id is not None else ("s", s.skill_id)
        w0, members = reqs.get(key, (0.0, []))
        reqs[key] = (max(w0, s.w_imp), members + [s.skill_id])
    return list(reqs.values())


def score_req(options: list[str], cv: dict[str, CvSkill],
              rel: Callable[[str, str], float] | None = None) -> tuple[float, CvSkill | None, str | None]:
    """-> (diem, ky nang CV dung de dap ung, lua chon JD duoc dap ung)."""
    best = (0.0, None, None)
    for opt in options:
        s = cv.get(opt)
        if s is not None and s.ev > best[0]:
            best = (s.ev, s, opt)
    if rel is not None:
        for s in cv.values():
            for opt in options:
                v = rel(s.skill_id, opt) * s.ev
                if v > best[0]:
                    best = (v, s, opt)
    return best


def coverage(jd_skills: list[JdSkill], cv: dict[str, CvSkill], required: bool,
             rel: Callable[[str, str], float] | None = None) -> float | None:
    reqs = requirements(jd_skills, required)
    total = sum(w for w, _ in reqs)
    if not reqs or total <= 0:
        return None
    return sum(w * score_req(opts, cv, rel)[0] for w, opts in reqs) / total


def skill_facts(jd_skills: list[JdSkill], cv: dict[str, CvSkill],
                relation: Callable[[str, str], str | None] | None = None) -> SkillFacts:
    """met: yeu cau bat buoc CV co dung ky nang; partial: chi co ky nang lien quan (qua KB);
    missing: yeu cau bat buoc chua thay (nhom "A hoac B" ghi lua chon dau tien)."""
    facts = SkillFacts()
    for _, opts in requirements(jd_skills, required=True):
        hit = max((cv[o] for o in opts if o in cv), key=lambda s: (s.ev, s.skill_id), default=None)
        if hit is not None:
            facts.met.append(SkillMet(skill=hit.skill_id, ev=hit.ev, evidence_id=hit.evidence_id))
            continue
        part = None
        if relation is not None:
            for s in sorted(cv.values(), key=lambda s: (-s.ev, s.skill_id)):
                for o in opts:
                    r = relation(s.skill_id, o)
                    if r in ("parent", "child", "sibling"):
                        part = SkillPartial(required=o, found=s.skill_id, relation=r)
                        break
                if part:
                    break
        if part is not None:
            facts.partial.append(part)
        else:
            facts.missing.append(opts[0])
    return facts
