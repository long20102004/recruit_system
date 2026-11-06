# Implementation Plan: KB (PostgreSQL) & Skill Entity Linking

**Branch**: `004-kb-skill-linking` (spec dir only) | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Add a PostgreSQL KB (own compose, port 5433), versioned seed CSVs built from cleaned train labels plus curated categories/relations, a loader with integrity checks, an in-memory skill linker (DB or CSV source), a silver-cleaning command and a linking-coverage measurement. Lives in `ai-service/kb/` (tooling) and `ai-service/app/kb/` (linker used by feature 005).

## Technical Context

**Language**: Python 3.14 venv · **New deps**: `psycopg[binary]` (PostgreSQL driver, runtime for loading from DB) · reuse `rapidfuzz`, `app.postprocess`.
**Storage**: PostgreSQL 16 in Docker (`infra/kb/docker-compose.yml`, port 5433, volume `kb_data`).
**Testing**: pytest unit tests with synthetic data + CSV-backed linker; one DB integration test marked `kb_db` (skipped unless `KB_DSN` is set).
**Constraints**: no change to API response (FR-009); no CV content in seeds (skills, school names, titles, headings are not personal data); real data stays in `ai-service/data/`.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Minimal Scope | PASS | No API/backend change; company KB, Neo4j, TYPICALLY_USES seeding excluded |
| II. Contracts | PASS | New DB schema documented in [contracts/kb-schema.md](contracts/kb-schema.md) for future consumers (005, Module 2) |
| III. Verification | PASS | Unit tests, integrity checks, real load into Docker PG, coverage measurement |
| IV. CV Data Security | PASS | Seeds contain vocabulary only; `.env` with credentials not committed |
| V. Maintainable | PASS | CSV seeds reviewable in git; loader idempotent |

## Design

```text
infra/kb/
├── docker-compose.yml      # postgres:16, 127.0.0.1:5433, env_file .env, volume
├── .env.example            # KB_DB=recruit_kb KB_USER=kb KB_PASSWORD=change-me
└── .gitignore              # .env
ai-service/
├── app/kb/
│   ├── __init__.py
│   ├── keys.py             # skill_key(s), school_key(s)
│   └── linker.py           # SkillLinker.from_csv(dir) / from_db(dsn); link(raw) -> list[Link]
├── kb/
│   ├── __init__.py
│   ├── sql/001_schema.sql
│   ├── seed/               # versioned CSV (UTF-8, header)
│   │   ├── categories.csv          id,name
│   │   ├── skills.csv              id,name,category,reviewed
│   │   ├── skill_aliases.csv       alias_key,skill_id,surface
│   │   ├── skill_edges.csv         src_id,rel,dst_id
│   │   ├── universities.csv        id,name,reviewed
│   │   ├── university_aliases.csv  alias_key,university_id,surface
│   │   ├── job_titles.csv          id,name,alias_key
│   │   ├── section_headings.csv    heading,section
│   │   ├── skill_categories_curated.csv  key,category,keep_composite   (curated, reviewed)
│   │   ├── skill_edges_curated.csv       src_name,rel,dst_name           (curated, reviewed)
│   │   └── university_curated.csv        key,canonical_name,extra_aliases (curated, reviewed)
│   ├── clean_silver.py     # python -m kb.clean_silver --in data/*.jsonl
│   ├── build_seed.py       # python -m kb.build_seed --train data/clean/train.jsonl --out kb/seed
│   ├── load.py             # python -m kb.load --dsn $KB_DSN [--schema-only]
│   └── measure.py          # python -m kb.measure --split data/clean/val.jsonl --seed kb/seed
└── tests/kb/ ...
```

### Keys (`app/kb/keys.py`)
`skill_key(s)`: `normalize` (accents/case), remove all chars except `[a-z0-9+#]`, then strip trailing `js` when the remainder ≥ 2 chars and the original contained `js` as suffix (`ReactJS`, `React.js`, `Node JS` → `react`, `node`). Examples: `Tailwind-CSS`→`tailwindcss`, `C#`→`c#`, `C++`→`c++`, `CI/CD`→`cicd`.
`school_key(s)`: `normalize`, drop prefixes `truong`, `dai hoc`, `hoc vien`, `university of`, `university`, punctuation; collapse spaces.

### Linker (`app/kb/linker.py`)
Index: `alias_key → skill_id`, `skill_id → (name, category)`, list of keys for fuzzy. `link(raw)`:
1. `clean_skill_list([raw])` (feature 002) → strips "Label:" and splits top-level commas → link each piece.
2. exact: `raw.strip().casefold()` equals a stored surface (casefold) → `exact`.
3. normalized: `skill_key(raw)` in index → `normalized`.
4. split: split on ` / `, `/`, ` & `, ` and `, `(`…`)` contents, `,` → link parts via 2–3 (no recursion beyond one level); if ≥ 1 part links → `split` (return linked parts; unlinked parts reported).
5. fuzzy: key length ≥ 4 → `rapidfuzz.process.extractOne(key, keys, scorer=fuzz.ratio, score_cutoff=90)` → `fuzzy`.
6. else `unlinked`.
`Link(raw, skill_id, name, category, method, score)`; `link_many(list)` dedupes by skill_id preserving order.

### Seed build
- Skills: group cleaned train gold skills by `skill_key`; canonical name = most frequent surface (tie → shortest, then alphabetical); aliases = all surfaces' keys (one key per group) plus each surface stored in `surface` column of its key row (first surface) — and an extra exact-surface map is derived at load from `skill_aliases.surface` + skill names.
- Composite surfaces (contain ` & `, `/`, ` (`) whose parts are themselves canonical skills are **not** created as skills (they link via split), unless `keep_composite=true` in `skill_categories_curated.csv` (e.g. `CI/CD`, `BRD/SRS`).
- Category: from `skill_categories_curated.csv` by key; missing → `Other`, `reviewed=false`.
- Edges: `skill_edges_curated.csv` by names → ids; unknown names fail the build.
- Universities: group train gold schools by `school_key`; merge groups via `university_curated.csv`; canonical name = most frequent full surface.
- Job titles: distinct train gold titles by `normalize` key, canonical = most frequent surface.
- Section headings: regex over `backend/.../SectionDictionary.java` `reg(CvSection.X, "..."...)`.
- Deterministic ordering and ids (sorted by name).

### Categories (fixed set)
`Programming Language, Framework/Library, Frontend, Mobile, Database, Cloud, DevOps/CI-CD, Testing/QA, Data/AI, Business Analysis, Design/UI-UX, Security, Tool/Platform, Methodology/Concept, Soft Skill, Other`.

### Loader
`001_schema.sql` (tables + constraints + FKs + `CHECK rel IN ('PART_OF','REQUIRES')`), then `TRUNCATE ... RESTART IDENTITY CASCADE` and `COPY`-style inserts in one transaction; post-checks: every skill has category, every alias references a skill, no PART_OF/REQUIRES cycles (recursive CTE), counts printed.

### Measurement
On cleaned val gold skills (val never used for seeding): per-method counts/shares; school linking share; writes `data/runs/kb/linking_report.{md,json}`.

## Subagent Assignment

| Task | Model |
|---|---|
| clean_silver + tests | agy `gemini-3.8-flash-medium` |
| keys + linker + tests | agy `gemini-3.8-flash-high` |
| build_seed + tests | agy `gemini-3.8-flash-high` |
| Curated categories/edges/universities proposal (data) | agy `gemini-3.8-flash-high`, reviewed by Claude |
| schema.sql + load.py + compose + integration test | agy `gemini-3.8-flash-medium` |
| measure.py | agy `gemini-3.8-flash-medium` |
| README | agy `gemini-3.8-flash-low` |
| Escalation | `openai/gpt-6.1-sol` → Claude |
