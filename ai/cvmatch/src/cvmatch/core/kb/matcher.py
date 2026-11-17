"""Nhan dien ky nang theo tu dien alias cua KB (thiet ke 04 A5, 05 B4, 02 muc 4).

Quy tac khop:
- cum dai khop truoc ("spring boot" truoc "spring", "react native" truoc "react");
- khop theo ranh gioi tu ("java" khong khop trong "javascript", ".net" khong khop trong "asp.net");
- alias de nham (`ambiguous_aliases`, va moi alias 1 ky tu) KHONG tu khop trong van ban tu do,
  nhung duoc khop khi la NGUYEN mot phan tu cua mang `skills` / `technologies`;
- ky nang loai `concept` chi khop trong van ban tu do bang alias du dai (nhieu tu, hoac
  >= `concept_min_len` ky tu): "api" don le khong ra REST API.

Cai dat: mot regex dang trie (chung tien to) cho moi tap alias -> quet mot luot, du nhanh
cho 100.000 CV. Van ban dau vao phai DA `normalize`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.text.normalize import normalize

# Ky tu ngan cach o dau/cuoi mot phan tu danh sach, bo di truoc khi tra nguyen phan tu
_ITEM_STRIP = " \t\n,;:()[]{}\"'`*-–—•"


@dataclass(frozen=True)
class Match:
    skill_id: str
    start: int
    end: int
    alias: str


def _trie_regex(words: list[str]) -> str:
    """Regex dang trie cho danh sach chuoi; nhanh tham lam tu dai -> ngan (nho backtracking)."""
    trie: dict = {}
    for w in words:
        node = trie
        for ch in w:
            node = node.setdefault(ch, {})
        node[""] = True

    def build(node: dict) -> str:
        end = "" in node
        branches = [re.escape(ch) + build(child) for ch, child in sorted(node.items()) if ch != ""]
        if not branches:
            return ""
        body = branches[0] if len(branches) == 1 else "(?:" + "|".join(branches) + ")"
        if end:
            # nhanh nay co the dung o day: thu phan dai truoc, khong duoc thi dung
            return "(?:" + body + ")?"
        return body

    return build(trie)


class SkillMatcher:
    def __init__(self, snapshot: KBSnapshot, *, concept_min_len: int = 5):
        self.snapshot = snapshot
        self.alias_to_skill = snapshot.alias_map()
        self.ambiguous = set(snapshot.ambiguous)

        free: list[str] = []
        for alias, sid in self.alias_to_skill.items():
            if alias in self.ambiguous or len(alias) <= 1:
                continue
            skill = snapshot.skills[sid]
            if skill.type == "concept" and not self._concept_alias_ok(alias, concept_min_len):
                continue
            free.append(alias)
        self.free_aliases = frozenset(free)
        self._re = (
            re.compile(r"(?<![\w.#+])(" + _trie_regex(sorted(free)) + r")(?![\w+#]|\.\w)")
            if free else None
        )

    @staticmethod
    def _concept_alias_ok(alias: str, min_len: int) -> bool:
        return len(re.findall(r"\w+", alias)) >= 2 or len(alias) >= min_len

    # ----------------------------------------------------------------- khop

    def find(self, text_norm: str) -> list[Match]:
        """Tim moi ky nang trong van ban tu do (da normalize). Khong chong lan, trai -> phai."""
        if not text_norm or self._re is None:
            return []
        return [
            Match(self.alias_to_skill[m.group(1)], m.start(1), m.end(1), m.group(1))
            for m in self._re.finditer(text_norm)
        ]

    def find_ids(self, text_norm: str) -> list[str]:
        return list(dict.fromkeys(m.skill_id for m in self.find(text_norm)))

    def match_list_item(self, item: str) -> list[Match]:
        """Mot phan tu cua mang `skills` / `technologies`.

        Nguyen phan tu trung mot alias (ke ca alias de nham, vd "Go") -> khop ky nang do.
        Khong thi do nhu van ban tu do (phan tu kieu "Java, Spring Boot"). Rong -> ky nang la
        (caller ghi `unknown_skill`).
        """
        norm = normalize(item)
        core = norm.strip(_ITEM_STRIP)
        sid = self.alias_to_skill.get(core)
        if sid is not None:
            start = norm.find(core)
            return [Match(sid, start, start + len(core), core)]
        return self.find(norm)

    # ----------------------------------------------------------------- tien ich

    def canonical_name(self, skill_id: str) -> str:
        """Ten chuan (dung cho buoc doi alias truoc BERTScore, 07 muc 2.1)."""
        return self.snapshot.skills[skill_id].name

    def protected_tokens(self) -> set[str]:
        """Tu (khong chua khoang trang) trong alias co ky tu dac biet (# + . / -) -> token duoc
        bao ve khi tach tu. Vd "asp.net core" -> "asp.net"."""
        return {w for a in self.alias_to_skill for w in a.split() if re.search(r"[#+./\-]", w)}
