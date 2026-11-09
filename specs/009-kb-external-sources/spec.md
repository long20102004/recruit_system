# Feature Specification: KB from external sources, normalised output, hidden KG

**Created**: 2026-11-05
**Status**: Clarified
**Input**: User: "KB phải được xây dựng từ các nguồn bên ngoài có thật, trích xuất nguồn vì tôi còn phải làm tài liệu, KB vẫn được sử dụng để normalize lại output của model, KG không phải tắt mà chỉ để ẩn output không cần thiết đi, do module 2 có thể tự làm được."

## Problem
The current KB (feature 004) was derived from the training labels plus LLM proposals reviewed by Claude; only the university list cites a real source (Wikipedia). It cannot be cited in the project documentation.

## Clarifications (2026-11-05)
- Normalisation **replaces** values in the response: `skills` and `personal_projects[].tech_stack` items linked to the KB become the KB canonical name ("ReactJS" → "React", "Postgress" → "PostgreSQL"); unlinked items stay as written in the CV; duplicates after mapping are removed (first occurrence kept).
- `education[].school` linked to the KB becomes the official name ("PTIT" → "Học viện Công nghệ Bưu chính Viễn thông"); unlinked schools stay as written.
- KG runs on every request (`KG_ENABLED` default back to `true`) but its fields are **hidden by default**; `POST /api/v1/extract-cv?include=kg` adds `skills_normalized`, `implied_skills`, `skills_detected`, `flags`, `education[].school_normalized`. `?include=raw` adds `raw_profile` (the grounded model output before normalisation) for evaluation and documentation. Both can be combined (`include=kg,raw`).
- Sources (all four): Stack Overflow Developer Survey (ODbL 1.0 / DbCL 1.0), Wikidata (CC0), GitHub Linguist (MIT), ESCO (CC BY 4.0, © European Union); universities: Wikipedia (CC BY-SA 4.0, already used) + Wikidata.

## User Scenarios

### US1 — Source snapshots with provenance (P1)
One command downloads every source into `ai-service/kb/sources/` (committed, no CV data): raw files as published plus `MANIFEST.json` (URL, retrieval date, revision/version, SHA-256, licence, attribution text). Building the seed uses only these snapshots (offline, reproducible).

### US2 — KB seed built only from the sources (P1)
`skills`, `skill_aliases`, `skill_edges`, `categories`, `universities`, `university_aliases`, `job_titles` are generated from the snapshots. Every row carries `source` (e.g. `stackoverflow-2026:WebFramework`, `wikidata:Q11248`, `linguist:C#`, `esco:<uri>`, `wikipedia:vi:75654510`). No value comes from training labels or LLM proposals. `SOURCES.md` lists each source with citation, licence, what was taken, and counts — ready to paste into the project documentation.
- Skills: Stack Overflow survey technology options (2024–2026) → canonical names + category from the survey question; Wikidata → aliases (en/vi labels and alt labels), Q-ids, and the gap-fill of frameworks/libraries/concepts the survey does not ask about; Linguist → programming-language aliases; ESCO → transversal (soft) skills.
- Gap-fill selection: Wikidata items matched from the skill vocabulary of the **synthetic/fictional** training CVs only (never real CVs), accepted only when the item is a software / programming / computing-concept class.
- KG edges: Wikidata properties only — P277 *programmed in* → `REQUIRES`, P361 *part of* → `PART_OF` (plus documented inverse P527 *has part*).
- Universities: Wikipedia list (current) + Wikidata Vietnamese universities (labels vi/en, P1813 short name).
- Job titles: ESCO ICT occupations (ISCO 25/35) preferred + alternative labels.
- Section headings are not knowledge: they stay a backend configuration file, out of the KB documentation.

### US3 — Normalised output, hidden KG (P1)
As clarified above. Backend `CandidateProfile` unchanged (CV fields only).

### US4 — Measurement (P2)
Report link rate of skills / schools on the 20 real test CVs (counts only) for the old and the new KB, and the eval scores with `include=raw`.

## Success Criteria
- SC-001: 100 % of seed rows have a `source` pointing to a snapshot in `MANIFEST.json`; `SOURCES.md` cites every source with licence.
- SC-002: Skill link rate on the 20 real CVs ≥ the old KB (73 %); school link rate ≥ old KB.
- SC-003: Default response contains only CV fields, normalised; `include=kg` / `include=raw` work; all tests pass; no CV data in logs or in `kb/sources/`.

## Assumptions
- ESCO has no Vietnamese labels: Vietnamese soft-skill phrases ("Làm việc nhóm") stay unlinked unless Wikidata has a Vietnamese label.
- Wikidata is queried with a generic User-Agent naming the project repository (no personal e-mail).
