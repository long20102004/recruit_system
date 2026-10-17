"""Rubric coverage: đánh dấu ý barem đã cover trong câu trả lời."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def criterion_covered(answer: str, criterion: dict[str, Any], threshold: int = 1) -> bool:
    """Heuristic: ý được coi là covered nếu khớp đủ `threshold` hint (substring)."""
    ans = normalize(answer)
    label = normalize(criterion.get("label", ""))
    hints = [normalize(h) for h in criterion.get("hints", []) if h]
    if label and label in ans:
        return True
    hits = sum(1 for h in hints if h and h in ans)
    return hits >= threshold


def score_coverage(answer: str, criteria: list[dict[str, Any]]) -> dict[str, Any]:
    covered: list[str] = []
    missing: list[str] = []
    weighted = 0.0
    for c in criteria:
        key = c["key"]
        weight = float(c.get("weight", 0.0))
        if criterion_covered(answer, c):
            covered.append(key)
            weighted += weight
        else:
            missing.append(key)
    return {
        "coverage_score": round(weighted, 4),
        "covered_keys": covered,
        "missing_keys": missing,
        "covered_labels": [c["label"] for c in criteria if c["key"] in covered],
        "missing_labels": [c["label"] for c in criteria if c["key"] in missing],
    }
