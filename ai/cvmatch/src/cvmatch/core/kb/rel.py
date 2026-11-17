"""He so lien quan giua ky nang `rel(a, b)` (thiet ke 02 muc 7) va ma tran nhom vai tro `M` (07 muc 5.6).

rel: cung ky nang 1,0 · cha/con 0,7 · anh em (chung cha, hoac chung Category sibling_ok) 0,4 · khac 0.
Gia tri lay tu config `rerank.rel` (UL). Anh em SUY RA luc truy van, khong luu (02 muc 2.5).
"""

from __future__ import annotations

from cvmatch.core.kb.snapshot import KBSnapshot


class SkillRelations:
    def __init__(self, snapshot: KBSnapshot, *, same: float = 1.0, parent_child: float = 0.7,
                 sibling: float = 0.4):
        self.same, self.parent_child, self.sibling = same, parent_child, sibling
        self.parents = {sid: set(s.parents) for sid, s in snapshot.skills.items()}
        self.cats = {sid: set(s.categories_sibling_ok) for sid, s in snapshot.skills.items()}

    @classmethod
    def from_config(cls, snapshot: KBSnapshot, rel_cfg) -> "SkillRelations":
        return cls(snapshot, same=rel_cfg.same, parent_child=rel_cfg.parent_child, sibling=rel_cfg.sibling)

    def relation(self, a: str, b: str) -> str | None:
        """'same' | 'parent' (a la cha cua b) | 'child' (a la con cua b) | 'sibling' | None."""
        if a == b:
            return "same"
        pa, pb = self.parents.get(a, set()), self.parents.get(b, set())
        if a in pb:
            return "parent"
        if b in pa:
            return "child"
        if (pa & pb) or (self.cats.get(a, set()) & self.cats.get(b, set())):
            return "sibling"
        return None

    def rel(self, a: str, b: str) -> float:
        r = self.relation(a, b)
        return {"same": self.same, "parent": self.parent_child, "child": self.parent_child,
                "sibling": self.sibling}.get(r, 0.0)


class RoleDistance:
    """M[g, g'] doi xung; cung nhom = 1; cap khong co = 0. `method`: hypothesis (mac dinh) | computed."""

    def __init__(self, snapshot: KBSnapshot, method: str = "hypothesis"):
        self.m: dict[frozenset, float] = {}
        for (a, b, meth), v in snapshot.role_distance.items():
            if meth == method:
                self.m[frozenset((a, b))] = v

    def __call__(self, g1: str | None, g2: str | None) -> float | None:
        if g1 is None or g2 is None:
            return None
        if g1 == g2:
            return 1.0
        return self.m.get(frozenset((g1, g2)), 0.0)
