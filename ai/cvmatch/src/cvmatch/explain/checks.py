"""EX4: kiem tra loi giai thich bang code (thiet ke 08 muc 4, 6).

1. Moi `evidence_id` duoc trich thuoc dung CV nay.
2. Moi ten cong nghe (tu dien KB) trong van ban thuoc {ky nang JD} ∪ {ky nang CV}
   (bo qua phan trich nguyen van trong ngoac kep: do la chuoi that cua JD/CV).
3. Khong co tu nhay cam / loi khuyen tuyen-loai.
4. Co cau gioi han khi `cap_applied`.
5. Ngoai cho trong do code dien, khong co chu so nao (kiem tren ban render da che du lieu).
Voi mau xac dinh, loi kiem = bug -> raise `ExplainCheckError`.
"""

from __future__ import annotations

import re
from pathlib import Path

from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.text.normalize import normalize

CAP_SENTENCE = "Điểm bị giới hạn"
_QUOTED = re.compile(r'"[^"\n]*"')
_DIGIT = re.compile(r"\d")


class ExplainCheckError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def load_forbidden(path: str | Path) -> list[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lower())
    return out


def find_problems(text: str, masked: str, *, cited_evidence: list[str], cv_evidence: set[str],
                  cap_applied: bool, forbidden: list[str], matcher: SkillMatcher | None = None,
                  allowed_skills: set[str] | None = None) -> list[str]:
    problems = []
    bad = [e for e in cited_evidence if e not in cv_evidence]
    if bad:
        problems.append(f"bang chung khong thuoc CV: {bad}")
    if matcher is not None and allowed_skills is not None:
        unquoted = _QUOTED.sub(" ", text)
        tech = {sid for sid in matcher.find_ids(normalize(unquoted))
                if matcher.snapshot.skills.get(sid) is not None
                and matcher.snapshot.skills[sid].type == "technology"}
        stray = sorted(tech - allowed_skills)
        if stray:
            problems.append(f"cong nghe khong thuoc JD/CV: {stray}")
    low = masked.lower()
    hits = [w for w in forbidden if w in low]
    if hits:
        problems.append(f"tu bi cam: {hits}")
    if cap_applied and CAP_SENTENCE not in text:
        problems.append("thieu cau gioi han diem (cap_applied)")
    digits = _DIGIT.findall(masked)
    if digits:
        problems.append(f"chu so khong do code dien: {len(digits)}")
    return problems
