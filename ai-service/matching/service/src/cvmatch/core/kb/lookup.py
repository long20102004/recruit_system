"""Tra chuc danh -> nhom vai tro, tu cap bac -> level_rank, nganh -> nhom (thiet ke 04 A6, 05 B5).

"Senior Java Developer" = chuc danh "java developer" + tu bo nghia "senior" (KB muc 1): A6/B5 do
hai thu doc lap.
"""

from __future__ import annotations

import re

from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.text.normalize import normalize, strip_diacritics

_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_EDGE = " \t-–—|/,;:.()[]"


def _alias_regex(aliases) -> re.Pattern | None:
    forms = sorted({a for a in aliases if a}, key=len, reverse=True)
    if not forms:
        return None
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(a) for a in forms) + r")(?!\w)")


# V-02: "Java Intern" bo cap bac con "java" - khong co trong role_title_map (map theo chuc danh day du)
FALLBACK_SUFFIXES = ("developer", "engineer")


class TitleLookup:
    def __init__(self, snapshot: KBSnapshot, *, fallback: bool = False):
        self.fallback = fallback
        self.level_map = dict(snapshot.level_map)
        self.title_map = dict(snapshot.title_map)
        self.major_map = dict(snapshot.major_map)
        # cho phep khop ca dang khong dau cua alias (CV go khong dau)
        for m in (self.level_map, self.title_map, self.major_map):
            for a, v in list(m.items()):
                m.setdefault(strip_diacritics(a), v)
        self._level_re = _alias_regex(self.level_map)
        self._title_re = _alias_regex(self.title_map)
        self._major_re = _alias_regex(self.major_map)

    # ----------------------------------------------------------------- cap bac

    def split_title(self, title: str | None) -> tuple[int | None, str]:
        """-> (level_rank | None, chuc danh goc da bo tu cap bac).

        Nhieu tu cap bac (vd "Senior/Lead") -> lay cap cao nhat.
        """
        t = normalize(title)
        if not t:
            return None, ""
        ranks: list[int] = []
        if self._level_re is not None:
            ranks = [self.level_map[m.group(1)] for m in self._level_re.finditer(t)]
            t = self._level_re.sub(" ", t)
        base = re.sub(r"\s+", " ", t).strip(_EDGE)
        base = re.sub(r"\(\s*\)", "", base).strip(_EDGE)
        return (max(ranks) if ranks else None), base

    # ----------------------------------------------------------------- nhom vai tro

    def role_group_of(self, base_title: str | None) -> str | None:
        """Chuc danh (da bo cap bac) -> nhom vai tro qua `role_title_map`; khong ra -> None.

        Thu: nguyen chuoi -> bo phan trong ngoac -> alias dai nhat nam trong chuoi.
        """
        t = normalize(base_title).strip(_EDGE)
        if not t:
            return None
        for cand in (t, _PAREN_RE.sub(" ", t).strip(_EDGE)):
            cand = re.sub(r"\s+", " ", cand)
            if cand in self.title_map:
                return self.title_map[cand]
        if self._title_re is not None:
            m = self._title_re.search(t)
            if m:
                return self.title_map[m.group(1)]
        if self.fallback and len(t.split()) <= 3:      # chuc danh ngan con lai sau khi bo cap bac (vd "java")
            for suf in FALLBACK_SUFFIXES:
                if (cand := f"{t} {suf}") in self.title_map:
                    return self.title_map[cand]
        return None

    def parse_title(self, title: str | None) -> tuple[int | None, str | None, str]:
        """-> (level_rank, role_group, base_title)."""
        level, base = self.split_title(title)
        return level, self.role_group_of(base), base

    # ----------------------------------------------------------------- nganh hoc

    def major_group_of(self, major: str | None) -> str | None:
        t = normalize(major).strip(_EDGE)
        if not t:
            return None
        if t in self.major_map:
            return self.major_map[t]
        if self._major_re is not None:
            m = self._major_re.search(t)
            if m:
                return self.major_map[m.group(1)]
        return None
