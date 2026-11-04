"""Skill-list cleaning for extracted CV profiles.

Self-contained (does not import ``text_match``) so it can run in parallel
with the rest of the post-processing package. Pure functions only.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_GROUP_LABEL = re.compile(r"^([^:()\n]{1,40}):[ \t]*(.*)$", re.DOTALL)
_LEADING_BULLET = re.compile(r"^[-*•·]+\s*")


def split_top_level(
    value: str,
    *,
    split_commas: bool = True,
    split_pipes: bool = True,
) -> list[str]:
    """Split ``value`` on top-level separators only.

    Separators are commas, semicolons, newlines and ``" | "`` (a pipe with
    whitespace on both sides). Text inside ``()`` or ``[]`` is never split,
    so ``"Spring Boot (Web, Data JPA)"`` stays one item. ``split_commas`` and
    ``split_pipes`` let callers keep commas/pipes that belong to the text
    (e.g. award names).
    """
    parts: list[str] = []
    buffer: list[str] = []
    depth = 0

    for index, char in enumerate(value):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(depth - 1, 0)
        elif depth == 0:
            if char in ";,\n\r":
                if char != "," or split_commas:
                    parts.append("".join(buffer))
                    buffer = []
                    continue
            elif char == "|" and split_pipes:
                previous = value[index - 1] if index else ""
                following = value[index + 1] if index + 1 < len(value) else ""
                if previous.isspace() and following.isspace():
                    parts.append("".join(buffer))
                    buffer = []
                    continue
        buffer.append(char)

    parts.append("".join(buffer))
    return parts


def _norm(value: str) -> str:
    """Case- and accent-insensitive key used for duplicate detection."""
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    without_marks = without_marks.replace("đ", "d").replace("Đ", "D")
    return " ".join(without_marks.casefold().split())


def _clean_one(value: str) -> str:
    """Strip a leading group label and bullet punctuation from one skill."""
    cleaned = _LEADING_BULLET.sub("", value.strip())
    match = _GROUP_LABEL.match(cleaned)
    if match and "/" not in match.group(1) and "\\" not in match.group(1):
        cleaned = match.group(2)
    return cleaned.strip(" \t;,")


def _bump(stats: Any, attr: str, amount: int) -> None:
    if stats is None or amount == 0:
        return
    setattr(stats, attr, getattr(stats, attr, 0) + amount)


def clean_skill_list(items: Any, stats: Any = None) -> list[str]:
    """Clean, trim and case-insensitively dedupe a list of skills."""
    if items is None:
        return []
    if isinstance(items, (str, dict)):
        items = [items]
    elif not isinstance(items, (list, tuple)):
        return []

    result: list[str] = []
    seen: set[str] = set()
    changed = 0

    for original in items:
        raw = original
        if isinstance(raw, dict):
            raw = raw.get("name") or raw.get("title") or ""
        if raw is None:
            raw = ""
        elif not isinstance(raw, str):
            raw = str(raw)

        cleaned = _clean_one(raw)
        if not cleaned:
            changed += 1
            continue

        for part in split_top_level(cleaned):
            candidate = part.strip(" \t;,")
            if not candidate:
                changed += 1
                continue

            key = _norm(candidate)
            if key in seen:
                changed += 1
                continue

            seen.add(key)
            result.append(candidate)
            if candidate != original:
                changed += 1

    _bump(stats, "skills_cleaned", changed)
    return result
