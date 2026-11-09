# Results: KB from external sources (feature 009)

## KB content (build 2026-11-05)
| Table | Rows | By source |
|---|---:|---|
| skills | 813 | Stack Overflow survey 477 (2024 104, 2025 56, 2026 317), ESCO 167, Wikidata 129, Stack Overflow tags 40 |
| skill_aliases | 2,284 | ESCO, Wikidata, survey, tags, Linguist |
| skill_edges (KG) | 132 | Wikidata P277 / P361 / P527 |
| universities | 387 | Wikipedia 282, Wikidata 104, official website 1 (FPT Polytechnic) |
| university_aliases | 1,259 | Wikidata, Wikipedia (+ spelling variants HCMC / "X College") |
| job_titles | 743 | ESCO |
Every row has `source`; `kb/sources/MANIFEST.json` holds URL, date, version, SHA-256, licence; `kb/seed/SOURCES.md` is the citation page. Snapshots 5.2 MB, no CV data.

## Link rate on the gold of the 20 real test CVs (counts only)
| | Old KB (004, labels + LLM proposals) | New KB, pass 1 | pass 2 | **final** |
|---|---|---|---|---|
| skills | 279/362 = 77.1 % | 52.8 % | 71.5 % | **276/362 = 76.2 %** |
| schools | 19/20 = 95 % | 65 % | 80 % | **17/20 = 85 %** |

SC-002 is **not fully met** (skills −0.9 pt, schools −10 pt). Reasons:
- The old KB was built from the training labels, so it held the exact free-text phrases CVs use ("Have the spirit of self-study", "Thành thạo kỹ năng HORENSO"); external sources do not have them.
- Schools missing: iSpace College and Nam Sai Gon Polytechnic College (no Wikidata item, not in the Wikipedia list; Nam Sai Gon was missing in the old KB too) and "FPT Polytechnic College" (English form of a name only published in Vietnamese).
- The remaining misses were diagnosed on the same 20 CVs used for this measurement; the fixes are generic (spelling variants, survey splits, established Stack Overflow tags selected from the synthetic vocabulary), but the 20-CV number is slightly optimistic.

## Normalisation on the v3 predictions of the 20 real CVs
276 predicted skills: 90 renamed to the canonical name, 114 already canonical, 72 kept as written (not in the KB); 14/19 schools linked.
Examples: ReactJS → React, NodeJS → Node.js, SQL Server → Microsoft SQL Server, OOP → Object-oriented programming, JWT Authentication → JSON Web Token, Bootstrap 5 → Bootstrap, Excel → Microsoft Excel, PTIT → Học viện Công nghệ Bưu chính Viễn thông.
Soft skills are not renamed (ESCO wording such as "work in teams" reads worse than the CV's "Làm việc nhóm"); their links are in `include=kg`.
KG: P277 "programmed in" → REQUIRES only for frameworks/libraries (tools such as Docker no longer imply their implementation language, Docker → Go removed). Multi-language libraries still list every implementation language (PyTorch → C, gRPC → Elixir): `implied_skills` is a hint, never evidence that the candidate knows the skill.
Known oddities: "RESTful API" → "Server-side web API" (Wikidata item whose alias is RESTful API); "GitLab" → "Gitlab" (survey spelling).

## Who did what
| Task | Agent |
|---|---|
| T001/T002 pass 1 (fetch, build, provenance, schema, SOURCES.md) | ChatGPT gpt-6.1-sol |
| T001/T002 pass 2 (survey splits, wider Wikidata classes, ESCO↔Wikidata soft skills, colleges, smaller snapshots) | ChatGPT gpt-6.1-sol |
| Pass 3: Stack Overflow tags source, linker spelling variants and "-"/"+" joins, school spelling variants, display names, no fuzzy to soft skills | Claude |
| T003 normalisation + `include=kg|raw` | Gemini gemini-3.8-flash-high; Claude: blacklist KG fields instead of a whitelist (kept `honors` when post-processing is off), soft skills verbatim |

## Not verified
- Loading the new seed into PostgreSQL (`kb.load` + `002_source.sql`) was not run (KB container stopped); CSV fallback path is tested.
- End-to-end eval with `include=raw` on the 20 CVs through the API (needs the model running).
