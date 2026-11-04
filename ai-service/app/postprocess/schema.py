"""Schema normalisation for extracted CV profiles.

Pure functions only: no I/O, no model, no logging. ``normalize_profile``
returns a new dict that always contains the full CandidateProfile schema,
renames known key aliases, drops unknown keys and coerces wrong types.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from app.postprocess.skills import split_top_level

TOP_LEVEL_ALIASES: dict[str, str] = {
    "honors": "honours",
    "awards": "honours",
    "certifications": "certificates",
    "projects": "personal_projects",
    "language": "languages",
    "skill": "skills",
}

PERSONAL_INFO_ALIASES: dict[str, str] = {
    "name": "full_name",
    "github": "github_url",
    "phone_number": "phone",
}

PERSONAL_INFO_KEYS: tuple[str, ...] = ("full_name", "email", "phone", "github_url")

ITEM_KEYS: dict[str, tuple[str, ...]] = {
    "education": ("school", "major", "start_year", "end_year", "gpa"),
    "experience": ("company", "job_title", "start_date", "end_date", "description"),
    "personal_projects": (
        "name",
        "role",
        "team_size",
        "start_date",
        "end_date",
        "github_url",
        "description",
        "tech_stack",
    ),
    "languages": ("language", "note"),
}

LIST_SECTIONS: tuple[str, ...] = ("education", "experience", "personal_projects")
STRING_LIST_SECTIONS: tuple[str, ...] = ("skills", "certificates", "honours")

_STRING_FIELDS = (
    "full_name",
    "email",
    "phone",
    "github_url",
    "school",
    "major",
    "company",
    "job_title",
    "name",
    "role",
    "language",
    "note",
    "start_date",
    "end_date",
    "start_year",
    "end_year",
    "gpa",
)

_BULLET_SPLIT = re.compile(r"\r?\n|[•·]")
_LEADING_BULLET = re.compile(r"^[-*•·]+\s*")


def _bump(stats: Any, attr: str, amount: int = 1) -> None:
    """Increment ``stats.attr`` when a stats object was supplied."""
    if stats is None or amount == 0:
        return
    setattr(stats, attr, getattr(stats, attr, 0) + amount)


def _empty_profile() -> dict:
    profile: dict[str, Any] = {
        "personal_info": {key: None for key in PERSONAL_INFO_KEYS},
        "objective": None,
    }
    for section in LIST_SECTIONS:
        profile[section] = []
    for section in STRING_LIST_SECTIONS:
        profile[section] = []
    profile["languages"] = []
    return profile


def _as_list(value: Any) -> list:
    """Coerce a value to a list without dropping or changing its items."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _rename_aliases(
    data: dict,
    aliases: dict[str, str],
    stats: Any,
    *,
    list_values: bool = False,
) -> dict:
    """Return a copy with alias keys renamed.

    When ``list_values`` is true both the canonical and alias values are
    coerced to lists and concatenated (canonical first, alias after), so no
    items are lost when both spellings are present.
    """
    result = dict(data)
    for alias, canonical in aliases.items():
        if alias not in result:
            continue
        value = result.pop(alias)
        if list_values:
            result[canonical] = _as_list(result.get(canonical)) + _as_list(value)
        elif canonical in result:
            current = result[canonical]
            if isinstance(current, list) and isinstance(value, list):
                result[canonical] = current + value
        else:
            result[canonical] = value
        _bump(stats, "keys_renamed")
    return result


def _as_str(value: Any, stats: Any) -> str | None:
    """Coerce a scalar field to a non-empty string (or None)."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            _bump(stats, "types_coerced")
            return None
        if stripped != value:
            _bump(stats, "types_coerced")
        return stripped
    _bump(stats, "types_coerced")
    if isinstance(value, (list, tuple)):
        # e.g. role: ["Developer"] -> "Developer" (never the Python repr "['Developer']")
        parts = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return ", ".join(parts) or None
    return str(value)


def _as_description(value: Any, stats: Any) -> list[str]:
    """Coerce a description into a list of non-empty bullet strings."""
    if value is None:
        return []
    if isinstance(value, str):
        _bump(stats, "types_coerced")
        parts = _BULLET_SPLIT.split(value)
        bullets = []
        for part in parts:
            cleaned = _LEADING_BULLET.sub("", part).strip()
            if cleaned:
                bullets.append(cleaned)
        return bullets
    if isinstance(value, (list, tuple)):
        bullets = []
        for item in value:
            if isinstance(item, str):
                cleaned = _LEADING_BULLET.sub("", item).strip()
            elif item is None:
                _bump(stats, "types_coerced")
                continue
            else:
                _bump(stats, "types_coerced")
                cleaned = str(item).strip()
            if cleaned:
                bullets.append(cleaned)
        return bullets
    _bump(stats, "types_coerced")
    return []


def _as_team_size(value: Any, stats: Any) -> int | None:
    """Coerce team size to an int, or None when it is not numeric."""
    if value is None:
        return None
    if isinstance(value, bool):
        _bump(stats, "types_coerced")
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        _bump(stats, "types_coerced")
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        _bump(stats, "types_coerced")
        match = re.search(r"\d+", value)
        return int(match.group()) if match else None
    _bump(stats, "types_coerced")
    return None


def _as_string_list(
    value: Any,
    stats: Any,
    *,
    split_commas: bool = True,
    split_pipes: bool = True,
) -> list[str]:
    """Coerce a section into a list of strings (skills/certificates/honours).

    String values (and string items) are split with ``split_top_level`` so
    grouped lists such as ``"Python, C++"`` become separate entries while
    parenthesised text stays intact.
    """
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        value = [value]
        _bump(stats, "types_coerced")
    elif not isinstance(value, (list, tuple)):
        _bump(stats, "types_coerced")
        return []

    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if not cleaned:
                _bump(stats, "types_coerced")
                continue
            pieces = split_top_level(
                cleaned,
                split_commas=split_commas,
                split_pipes=split_pipes,
            )
        elif isinstance(item, dict):
            _bump(stats, "types_coerced")
            raw = item.get("name") or item.get("title")
            cleaned = raw.strip() if isinstance(raw, str) else str(item).strip()
            pieces = [cleaned]
        elif item is None:
            _bump(stats, "types_coerced")
            continue
        else:
            _bump(stats, "types_coerced")
            pieces = [str(item).strip()]

        for piece in pieces:
            cleaned = piece.strip(" \t;,")
            if cleaned:
                result.append(cleaned)
    return result


def _clean_item(item: dict, keys: tuple[str, ...], stats: Any) -> dict:
    """Keep only schema keys of a section item and coerce its values."""
    result: dict[str, Any] = {}
    for key in keys:
        value = item.get(key)
        if key == "description":
            result[key] = _as_description(value, stats)
        elif key == "team_size":
            result[key] = _as_team_size(value, stats)
        elif key == "tech_stack":
            result[key] = _as_string_list(value, stats)
        elif key in _STRING_FIELDS:
            result[key] = _as_str(value, stats)
        else:
            result[key] = value
    return result


def _as_item_list(value: Any, keys: tuple[str, ...], stats: Any) -> list[dict]:
    """Coerce a section into a list of item dicts."""
    if value is None:
        return []
    if isinstance(value, dict):
        _bump(stats, "types_coerced")
        value = [value]
    elif not isinstance(value, (list, tuple)):
        _bump(stats, "types_coerced")
        return []

    result: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            result.append(_clean_item(item, keys, stats))
        else:
            _bump(stats, "types_coerced")
    return result


def normalize_profile(data: Any, stats: Any = None) -> dict:
    """Return a schema-complete copy of ``data`` (never mutates the input)."""
    if not isinstance(data, dict):
        return _empty_profile()

    source = _rename_aliases(
        copy.deepcopy(data), TOP_LEVEL_ALIASES, stats, list_values=True
    )
    profile = _empty_profile()

    personal_info = source.get("personal_info")
    if isinstance(personal_info, dict):
        personal_info = _rename_aliases(personal_info, PERSONAL_INFO_ALIASES, stats)
        profile["personal_info"] = {
            key: _as_str(personal_info.get(key), stats) for key in PERSONAL_INFO_KEYS
        }
    elif personal_info is not None:
        _bump(stats, "types_coerced")

    profile["objective"] = _as_str(source.get("objective"), stats)

    for section in LIST_SECTIONS:
        profile[section] = _as_item_list(source.get(section), ITEM_KEYS[section], stats)

    for section in STRING_LIST_SECTIONS:
        if section in ("certificates", "honours"):
            # Award/certificate names often contain commas: only split on
            # newlines and semicolons for these sections.
            profile[section] = _as_string_list(
                source.get(section),
                stats,
                split_commas=False,
                split_pipes=False,
            )
        else:
            profile[section] = _as_string_list(source.get(section), stats)

    profile["languages"] = _as_item_list(
        source.get("languages"), ITEM_KEYS["languages"], stats
    )
    return profile
