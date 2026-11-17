"""Chuan bi dau vao BERTScore (thiet ke 07 muc 2.1), ap NHU NHAU cho cau JD va gach CV:

1. lay `text_raw` (NFC, giu dau, giu hoa/thuong) - khong dung ban chu thuong `text`;
2. doi alias ve ten chuan qua KB (`canonicalize_aliases`): "K8s" -> "Kubernetes", "ReactJS" -> "React".
   Chi doi khi alias KHAC ten chuan (khong doi "Java" -> "java" chi vi KB ghi ten chuan chu thuong);
3. che so (`mask_numbers`): moi so dung rieng (ke ca "40%", "3.5") -> "N". So nam trong ten cong
   nghe ("K8s", "S3", "ES6") khong bi che vi khong dung rieng;
4. khong ghep chuc danh vao gach.

Tra them ban do vi tri (doan van ban da chuan bi -> doan `text_raw`) de Explain to dam dung chuoi goc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.text.normalize import normalize, to_raw

_NUMBER_RE = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*\s?%?(?![\w])")


@dataclass
class Prepared:
    raw: str                                   # text_raw (sau to_raw)
    text: str                                  # van ban dua vao model
    segments: list[tuple[int, int, int, int]] = field(default_factory=list)  # (p0, p1, r0, r1)

    def to_raw_span(self, p0: int, p1: int) -> tuple[int, int]:
        """Doan [p0, p1) cua `text` -> doan tuong ung trong `raw`. Doan nam trong phan bi thay
        (alias, so) thi lay ca phan goc bi thay."""
        def seg_at(p: int):
            for s in self.segments:
                if s[0] <= p < s[1]:
                    return s
            return self.segments[-1] if self.segments else (0, 0, 0, 0)

        a, b, c, d = seg_at(p0)
        same = (b - a) == (d - c) and self.text[a:b] == self.raw[c:d]
        r0 = c + (p0 - a) if same else c
        a, b, c, d = seg_at(max(p1 - 1, p0))
        same = (b - a) == (d - c) and self.text[a:b] == self.raw[c:d]
        r1 = c + (p1 - a) if same else d
        return r0, r1


def _apply(raw: str, edits: list[tuple[int, int, str]]) -> Prepared:
    """edits: (r0, r1, chuoi thay) khong chong lan, sap tang."""
    out, segs, pos, p = [], [], 0, 0
    for r0, r1, rep in edits:
        if r0 > pos:
            out.append(raw[pos:r0])
            segs.append((p, p + r0 - pos, pos, r0))
            p += r0 - pos
        out.append(rep)
        segs.append((p, p + len(rep), r0, r1))
        p += len(rep)
        pos = r1
    if pos < len(raw):
        out.append(raw[pos:])
        segs.append((p, p + len(raw) - pos, pos, len(raw)))
    return Prepared(raw=raw, text="".join(out), segments=segs)


def prepare(text_raw: str, matcher: SkillMatcher | None, *, canonicalize_aliases: bool = True,
            mask_numbers: bool = True) -> Prepared:
    raw = to_raw(text_raw, keep_newlines=False)
    edits: list[tuple[int, int, str]] = []
    if canonicalize_aliases and matcher is not None:
        low = raw.lower()
        if len(low) == len(raw):  # lower() giu do dai -> vi tri khop tren ban thuong dung cho ban goc
            for m in matcher.find(low):
                name = matcher.canonical_name(m.skill_id)
                if normalize(name) != m.alias:
                    edits.append((m.start, m.end, name))
    if mask_numbers:
        taken = [(a, b) for a, b, _ in edits]
        for m in _NUMBER_RE.finditer(raw):
            if not any(a < m.end() and m.start() < b for a, b in taken):
                edits.append((m.start(), m.end(), "N"))
    edits.sort()
    return _apply(raw, edits)
