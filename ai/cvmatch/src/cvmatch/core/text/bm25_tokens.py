"""Token BM25 (thiet ke 04 A9, 05 B7). Ba truong rieng, khong tron:

- `bm25_acc`:    token co dau (sau tach tu)
- `bm25_noacc`:  token khong dau (mac dinh cho BM25, khop ca CV go khong dau)
- `skill_tokens`: `skill_<skill_id>` cho moi ky nang da gan ma
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from cvmatch.core.text.normalize import strip_diacritics
from cvmatch.core.text.segment import Segmenter

_HAS_ALNUM = re.compile(r"\w", re.UNICODE)


def tokens_acc(text: str, segmenter: Segmenter) -> list[str]:
    """Van ban DA CHUAN HOA -> token co dau, bo token chi gom dau cau."""
    return [t.lower() for t in segmenter.segment(text) if _HAS_ALNUM.search(t.replace("_", ""))]


def tokens_noacc(tokens: Iterable[str]) -> list[str]:
    return [strip_diacritics(t) for t in tokens]


def skill_tokens(skill_ids: Iterable[str]) -> list[str]:
    return sorted({f"skill_{sid.lower()}" for sid in skill_ids})


def bm25_fields(text: str, skill_ids: Iterable[str], segmenter: Segmenter) -> dict[str, list[str]]:
    acc = tokens_acc(text, segmenter)
    return {"bm25_acc": acc, "bm25_noacc": tokens_noacc(acc), "skill_tokens": skill_tokens(skill_ids)}
