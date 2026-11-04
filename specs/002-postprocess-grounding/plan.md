# Implementation Plan: Post-processing & Grounding (Tier 3)

**Branch**: `002-postprocess-grounding` (spec dir only) | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Add a pure-Python post-processing package in `ai-service/app/postprocess/` applied in `POST /api/v1/extract-cv` after `extract_json`. It normalises keys/types, cleans skills, grounds entities and contacts against the CV text (accent/case-insensitive, rapidfuzz ≥ 85 snap-to-source), and removes fake experiences. Enabled by default, switchable by env for ablation; importable offline for evaluation (feature 003).

## Technical Context

**Language/Version**: Python 3.14 venv (code ≥ 3.10)
**Primary Dependencies**: `rapidfuzz` (new; C++ fuzzy matching, fast, MIT), stdlib `unicodedata`, `re`
**Testing**: pytest (from 001), synthetic CV fixtures only
**Performance Goals**: < 100 ms per CV (SC-004)
**Constraints**: response shape unchanged; no values in logs (constitution IV)
**Scale/Scope**: ~5 new modules, 1 route edit, config flag, tests, README

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Minimal Scope | PASS | KB linking, Base(a,b) split, job_title proximity excluded |
| II. Explicit Contracts | PASS | Response keys/shape unchanged; values may be removed/corrected (documented in README) |
| III. Verification | PASS | Unit tests per rule + route test + timing test |
| IV. CV Data Security | PASS | Logs counts only; synthetic fixtures |
| V. Maintainable | PASS | Small single-purpose modules, pure functions |

## Design

```text
ai-service/app/postprocess/
├── __init__.py      # from .pipeline import postprocess, PostprocessStats
├── text_match.py    # normalize, normalize_with_map, contains, find_span, digits
├── schema.py        # KEY_ALIASES, normalize_profile(data, stats) -> dict
├── skills.py        # clean_skill_list(items, stats) -> list[str]
├── grounding.py     # ground_profile(profile, cv_text, stats) -> dict
└── pipeline.py      # postprocess(data, cv_text) -> tuple[dict, PostprocessStats]
```

### text_match.py (API used by grounding)
- `normalize(s) -> str`: NFD, drop combining marks, `đ/Đ→d`, lowercase, collapse whitespace, strip.
- `normalize_with_map(s) -> tuple[str, list[int]]`: same, plus `map[i]` = index in original `s` of normalized char `i` (needed to cut the original CV span).
- `contains(cv_norm, value) -> bool`: `normalize(value)` non-empty and substring of `cv_norm`.
- `find_span(value, cv_text, threshold=85) -> str | None`: if exact normalized containment → return original CV substring; if `len(normalize(value)) < 3` → None; else `rapidfuzz.fuzz.partial_ratio_alignment(normalize(value), cv_norm)`; score ≥ threshold → map `dest_start/dest_end` back to original text, strip → return; else None.
- `digits(s) -> str`.

### schema.py
- `KEY_ALIASES`: top-level `honors→honours`, `awards→honours`, `certifications→certificates`, `projects→personal_projects`, `language→languages`, `skill→skills`; personal_info `name→full_name`, `github→github_url`, `phone_number→phone`.
- Complete schema (scalars `None`, lists `[]`), drop unknown top-level keys, coerce: section lists (dict → `[dict]`, other → `[]`), item dicts keep only schema keys (from requirements.md), `description` str → `[str]` (split on newlines/bullets), `team_size` → int or None, years/gpa → str or None, empty strings → None, list of strings for skills/certificates/honours (dict items → their `name`/`title` value or `str`).

### skills.py
- Strip leading `Label:` (label ≤ 40 chars, no `(`), strip bullets/punctuation, drop empty, dedupe case-insensitive (normalize) preserving order. Do **not** split `Base (a, b)`.

### grounding.py (order)
1. Contacts: email/github_url nulled if `not contains`; phone nulled if `digits(phone)` (≥ 8 digits) not in `digits(cv_text)`; full_name → `find_span` or None.
2. Experience: for each item → company `find_span`; None → removed (record for merge); else snap. Then type check: title empty or matches `^(sinh viên|student|học viên|thực tập sinh?)$`… (only the first three per spec; "thực tập sinh"/intern is real experience and KEPT) → remove; company looks like school (`đại học|university|trường|học viện|college|academy|institute|cao đẳng|thpt`) and title not teaching/staff (`giảng viên|lecturer|teacher|giáo viên|trợ giảng|teaching assistant|nghiên cứu viên|research|staff|nhân viên|cán bộ`) → remove.
3. Merge: removed-for-grounding experiences whose normalized company contains a project's normalized name (len ≥ 3) → extend that project's description with the bullets (dedupe).
4. Education: school `find_span` or remove. Projects: name `find_span` or remove.
5. objective: `find_span` (≥ 85) else None. certificates/honours: keep items with `find_span`. languages: keep if language (or alias: English/Tiếng Anh/Anh, Japanese/Tiếng Nhật/Nhật, Korean/Hàn, Chinese/Trung, French/Pháp, German/Đức, Vietnamese/Việt) or note is contained.
6. Remove exact duplicate items in each list section.

### pipeline.py
- `@dataclass PostprocessStats` (counters, `as_dict()`), `postprocess(data, cv_text)`: `normalize_profile` → skills/tech_stack cleaning → `ground_profile` → return. Pure, no logging.

### Integration
- `config.POSTPROCESS_ENABLED` (env `POSTPROCESS_ENABLED`, default true; false values `0/false/no/off`).
- `routes.py`: after `extract_json`, if enabled: `try: data, stats = postprocess(data, cv_text); logger.info("request_id=%s postprocess %s", id, stats.as_dict())` `except Exception as e: logger.error(type only)` and keep un-processed data.
- `requirements.txt`: add `rapidfuzz`.

## Subagent Assignment

| Task | Tier / model |
|---|---|
| text_match.py + tests | Gemini `gemini-3.8-flash-high` (index mapping) |
| schema.py, skills.py + tests | Free `deepseek-v4.1-flash-free` / `glm-5.3-flash-free` |
| grounding.py + tests | Gemini `gemini-3.8-flash-high` |
| pipeline + config + routes + integration tests, README | Gemini `gemini-3.8-flash-medium`, Free `mimo-v2.6-flash-free` |
| Escalation | ChatGPT `openai/gpt-6.1-sol` → Claude |

## Complexity Tracking

None.
