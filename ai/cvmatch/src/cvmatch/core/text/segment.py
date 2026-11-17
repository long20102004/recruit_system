"""Tach tu tieng Viet (A9, B7) sau mot interface de doi cong cu duoc (diem mo 10).

Cong cu tach tu hay cat sai ten cong nghe (pyvi: `c++` -> `c + +`, `node.js` -> `node . js`),
nen token duoc bao ve duoc thay bang placeholder chi gom chu cai truoc khi tach va tra lai sau.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol


class Segmenter(Protocol):
    def segment(self, text: str) -> list[str]:
        """Van ban (da chuan hoa) -> danh sach token; tu ghep noi bang '_'."""
        ...


def _alpha_code(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(97 + r) + s
    return s


class _Protector:
    """Thay token bao ve bang placeholder `zzptok<abc>zz` (pyvi giu nguyen chuoi chu cai)."""

    def __init__(self, protected: Iterable[str]):
        toks = sorted({t for t in protected if t}, key=len, reverse=True)
        self._tokens = toks
        self._ph = {t: f"zzptok{_alpha_code(i)}zz" for i, t in enumerate(toks)}
        self._back = {v: k for k, v in self._ph.items()}
        self._re = (
            re.compile(r"(?<!\w)(" + "|".join(re.escape(t) for t in toks) + r")(?![\w+#])")
            if toks else None
        )

    def protect(self, text: str) -> str:
        if self._re is None:
            return text
        return self._re.sub(lambda m: f" {self._ph[m.group(1)]} ", text)

    def restore(self, token: str) -> str:
        return self._back.get(token, token)


class WhitespaceSegmenter:
    """Tach theo khoang trang + tach dau cau ra rieng; khong ghep tu. Dung cho test / du phong."""

    _TOKEN_RE = re.compile(r"\w+|[^\w\s]")

    def __init__(self, protected: Iterable[str] = ()):
        self._p = _Protector(protected)

    def segment(self, text: str) -> list[str]:
        out = []
        for tok in self._TOKEN_RE.findall(self._p.protect(text)):
            out.append(self._p.restore(tok))
        return out


class PyViSegmenter:
    """Tach tu bang pyvi (CRF). Giu nguyen token bao ve."""

    def __init__(self, protected: Iterable[str] = ()):
        from pyvi import ViTokenizer  # import tre: thu vien nang

        self._tok = ViTokenizer
        self._p = _Protector(protected)

    def segment(self, text: str) -> list[str]:
        if not text.strip():
            return []
        out: list[str] = []
        for line in text.split("\n"):
            if line.strip():
                out.extend(self._p.restore(t) for t in self._tok.tokenize(self._p.protect(line)).split())
        return out


def make_segmenter(name: str, protected: Iterable[str] = ()) -> Segmenter:
    if name == "pyvi":
        return PyViSegmenter(protected)
    if name == "whitespace":
        return WhitespaceSegmenter(protected)
    raise ValueError(f"segmenter chua ho tro: {name}")
