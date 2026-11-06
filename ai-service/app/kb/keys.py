"""Normalisation keys for KB skill and school lookup."""

from __future__ import annotations

import re

from app.postprocess.text_match import normalize

__all__ = ["skill_key", "school_key"]

_SCHOOL_PREFIXES: tuple[str, ...] = (
    "truong ",
    "dai hoc ",
    "hoc vien ",
    "university of ",
    "university ",
    "the ",
)


def skill_key(s: str | None) -> str:
    """Normalize skill surface to canonical lookup key.

    Rules:
    - k = normalize(s)
    - had_js = re.search(r"(\.|\s)?js$", k) is not None
    - k = re.sub(r"[^a-z0-9+#]", "", k)
    - if had_js and k.endswith("js") and len(k) - 2 >= 2: k = k[:-2]
    """
    if not s:
        return ""
    if not isinstance(s, str):
        s = str(s)
    k = normalize(s)
    had_js = re.search(r"(\.|\s)?js$", k) is not None
    k = re.sub(r"[^a-z0-9+#]", "", k)
    if had_js and k.endswith("js") and len(k) - 2 >= 2:
        k = k[:-2]
    return k


def school_key(s: str | None) -> str:
    """Normalize university / school name to canonical lookup key.

    Rules:
    - k = normalize(s)
    - replace punctuation ([^a-z0-9 ]) with space
    - loop-strip prefixes: "truong ", "dai hoc ", "hoc vien ", "university of ", "university ", "the "
    - strip suffix " university"
    - collapse spaces, strip
    """
    if not s:
        return ""
    if not isinstance(s, str):
        s = str(s)
    k = normalize(s)
    k = re.sub(r"[^a-z0-9 ]", " ", k)
    k = " ".join(k.split())
    changed = True
    while changed:
        changed = False
        for prefix in _SCHOOL_PREFIXES:
            if k.startswith(prefix):
                k = k[len(prefix):].lstrip()
                changed = True
                break
    if k.endswith(" university"):
        k = k[:-len(" university")]
    return " ".join(k.split()).strip()
