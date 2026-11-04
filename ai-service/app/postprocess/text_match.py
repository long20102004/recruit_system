"""Text normalization, matching and span extraction utilities for CV grounding."""

from __future__ import annotations

import unicodedata
from rapidfuzz.fuzz import partial_ratio_alignment

__all__ = [
    "normalize",
    "normalize_with_map",
    "contains",
    "find_span",
    "digits",
]


def normalize_with_map(s: str | None) -> tuple[str, list[int]]:
    """Normalize a string and return a mapping from normalized char index to original char index.

    Algorithm:
    1. Iterate over each character in the original string with its original index.
    2. Decompose the character using Unicode NFD.
    3. Drop combining marks (Unicode category starting with 'M').
    4. Convert 'đ' / 'Đ' (and eth) to 'd'.
    5. Convert whitespace to ' ', and lowercase letters.
    6. Strip leading and trailing whitespace.
    7. Collapse consecutive whitespace into a single space.

    Returns:
        tuple[str, list[int]]: (normalized_string, char_map) where char_map[i] is the
        index in the original string of character i in normalized_string.
    """
    if not s:
        return "", []
    if not isinstance(s, str):
        s = str(s)

    mapped_chars: list[tuple[str, int]] = []
    for orig_idx, char in enumerate(s):
        decomp = unicodedata.normalize("NFD", char)
        for c in decomp:
            if unicodedata.category(c).startswith("M"):
                continue
            if c in ("đ", "Đ", "ð", "Ð"):
                c = "d"
            elif c.isspace():
                c = " "
            else:
                c = c.lower()
            mapped_chars.append((c, orig_idx))

    # Strip leading whitespace
    start = 0
    while start < len(mapped_chars) and mapped_chars[start][0] == " ":
        start += 1

    # Strip trailing whitespace
    end = len(mapped_chars)
    while end > start and mapped_chars[end - 1][0] == " ":
        end -= 1

    if start >= end:
        return "", []

    # Collapse consecutive whitespace into a single space
    norm_chars: list[str] = []
    char_map: list[int] = []
    prev_was_space = False

    for c, orig_idx in mapped_chars[start:end]:
        if c == " ":
            if not prev_was_space:
                norm_chars.append(" ")
                char_map.append(orig_idx)
                prev_was_space = True
        else:
            norm_chars.append(c)
            char_map.append(orig_idx)
            prev_was_space = False

    return "".join(norm_chars), char_map


def normalize(s: str | None) -> str:
    """Normalize string: NFD, drop combining marks, đ/Đ->d, lowercase, collapse whitespace, strip."""
    norm, _ = normalize_with_map(s)
    return norm


def contains(cv_norm: str, value: str) -> bool:
    """Check if normalized value is non-empty and a substring of normalized cv text.

    Supports cv_norm being either pre-normalized text or raw text with diacritics/casing.
    """
    if not cv_norm or not value:
        return False
    val_norm = normalize(value)
    if not val_norm:
        return False
    if val_norm in cv_norm:
        return True
    return val_norm in normalize(cv_norm)


def find_span(
    value: str,
    cv_text: str,
    threshold: float = 85.0,
    *,
    cv_norm: str | None = None,
    cv_map: list[int] | None = None,
) -> str | None:
    """Find and return original CV substring matching value.

    1. If exact normalized containment -> return original CV substring.
    2. If len(normalize(value)) < 3 -> None (no fuzzy snap for short names).
    3. Else rapidfuzz.fuzz.partial_ratio_alignment(s1=val_norm, s2=cv_norm, score_cutoff=threshold).
       If alignment meets threshold, map dest_start/dest_end back to original text, strip -> return.
       Else None.
    """
    if not value or not cv_text:
        return None

    val_norm = normalize(value)
    if not val_norm:
        return None

    if cv_norm is None or cv_map is None:
        cv_norm, cv_map = normalize_with_map(cv_text)

    if not cv_norm or not cv_map:
        return None

    # 1. Exact normalized containment
    if val_norm in cv_norm:
        idx = cv_norm.find(val_norm)
        dest_start = idx
        dest_end = idx + len(val_norm)
        return _cut(cv_text, cv_map[dest_start], cv_map[dest_end - 1] + 1, widen=True)

    # 2. Short names (< 3 characters) require exact containment
    if len(val_norm) < 3:
        return None

    # 3. Fuzzy match with rapidfuzz
    alignment = partial_ratio_alignment(
        s1=val_norm,
        s2=cv_norm,
        score_cutoff=threshold,
    )
    if alignment is None or alignment.score < threshold:
        return None

    dest_start = alignment.dest_start
    dest_end = alignment.dest_end
    if dest_end <= dest_start or dest_end > len(cv_map) or dest_start < 0:
        return None

    # Fuzzy alignment may cut inside a word: widen to word boundaries.
    return _cut(cv_text, cv_map[dest_start], cv_map[dest_end - 1] + 1, widen=True)


def _cut(text: str, start: int, end: int, widen: bool = False) -> str | None:
    """Return text[start:end] (optionally widened to word boundaries), whitespace-collapsed."""
    if widen:
        while start > 0 and text[start - 1].isalnum():
            start -= 1
        while end < len(text) and text[end].isalnum():
            end += 1
    span = " ".join(text[start:end].split())
    return span or None


def digits(s: str | None) -> str:
    """Extract only digit characters from string."""
    if not s:
        return ""
    return "".join(c for c in str(s) if c.isdigit())
