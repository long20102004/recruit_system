"""Danh sach mau (thiet ke 04 A7, 05 B6, 08 muc 6): phu dinh, hoc tap, trach nhiem chung chung,
chuoi dang ngo prompt injection. Moi file mot cum mot dong, `#` la chu thich.

So khop tren van ban da `normalize`, theo ranh gioi tu, ca dang co dau va khong dau.
"""

from __future__ import annotations

import re
from pathlib import Path

from cvmatch.core.text.normalize import normalize, strip_diacritics


def read_pattern_file(path: str | Path) -> list[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(normalize(line))
    return out


class PatternList:
    def __init__(self, patterns: list[str]):
        self.patterns = patterns
        forms = sorted({f for p in patterns for f in (p, strip_diacritics(p))}, key=len, reverse=True)
        self._re = (
            re.compile(r"(?<!\w)(?:" + "|".join(re.escape(f) for f in forms) + r")(?!\w)")
            if forms else None
        )

    def search(self, text: str) -> str | None:
        """Tra ve cum mau khop dau tien (hoac None). `text` nen da chuan hoa."""
        if self._re is None or not text:
            return None
        m = self._re.search(normalize(text))
        return m.group(0) if m else None

    def __contains__(self, text: str) -> bool:
        return self.search(text) is not None


class Patterns:
    def __init__(self, negation: PatternList, coursework: PatternList, generic_resp: PatternList,
                 injection: PatternList):
        self.negation = negation
        self.coursework = coursework
        self.generic_resp = generic_resp
        self.injection = injection

    @classmethod
    def from_config(cls, cfg) -> "Patterns":
        return cls(**{n: PatternList(read_pattern_file(cfg.pattern_path(n)))
                      for n in ("negation", "coursework", "generic_resp", "injection")})

    def has_negation(self, text: str) -> bool:
        return text in self.negation

    def is_coursework(self, text: str) -> bool:
        return text in self.coursework

    def is_generic_resp(self, text: str) -> bool:
        return text in self.generic_resp

    def suspected_injection(self, text: str) -> bool:
        return text in self.injection
