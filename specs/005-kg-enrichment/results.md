# Results: KG Enrichment (feature 005)

**Date**: 2026-11-04 · Variant C = B + KG enrichment, computed offline on the cached Colab T4 predictions of feature 003 (same model output for A/B/C). KB: seed CSV build of 2026-11-04 (643 skills, 136 relations, 298 universities).

| Metric | val B | val C | val_swap B | val_swap C |
|---|---:|---:|---:|---:|
| Hallucination rate | 0.002 | 0.002 | 0.002 | 0.002 |
| experience.company F1 | 0.918 | 0.918 | 0.926 | 0.926 |
| education.school F1 | 0.961 | 0.961 | 0.966 | 0.966 |
| skills F1 (string match) | 0.839 | 0.839 | 0.829 | 0.829 |
| **skills F1 (canonical KB ids)** | 0.852 | 0.852 | 0.841 | 0.841 |
| implied skills / CV | — | 1.67 | — | 1.69 |
| unlinked predicted skills | — | 8.2% | — | 7.8% |
| KG time / CV | — | 3.0 ms | — | 3.3 ms |

## Reading the numbers

- Enrichment is **additive**: it never changes extracted values, so extraction metrics of C equal B by design.
- Comparing skills on canonical KB ids instead of strings raises skills F1 by ~1.3–1.5 points (0.839 → 0.852 on val): spelling variants (ReactJS / React.js, Postgress / PostgreSQL) now count as the same skill. This is the measurable value of linking for matching (Module 2); it is a representation gain, not better extraction.
- Each CV gets ~1.7 implied skills with explicit reasons (e.g. Spring Boot ⇒ Java, ReactJS ⇒ JavaScript); they are kept out of `skills`.
- 8% of predicted skills stay unlinked (soft-skill sentences, technologies outside the train vocabulary); they are reported with `method = "unlinked"` and counted in the `SKILLS_UNLINKED` flag.
- Circularity caveat (feature 004) still applies: the skill KB is built from the same label distribution.

## Integration checks

- ai-service: 199 tests pass (+1 DB integration test on `recruit_kb_test`); KB loaded from PostgreSQL at startup with CSV fallback; `/health` reports `kb`.
- Backend: `CandidateProfile` exposes `skills_normalized`, `implied_skills`, `flags`, `education[].school_normalized`; `mvn test` 4/4 (3 new contract tests incl. legacy JSON without the fields).
- End-to-end smoke (synthetic PDF → backend `/api/v1/cv/analyze-pdf` → ai-service on CPU): new fields present, "Postgress" → PostgreSQL, implied JavaScript/SQL with reasons, flags contain codes/counts only, logs contain counts only.

## Fixes made during this feature

- KB: manual alias file `skill_aliases_curated.csv` (Postgres, PosgeSQL → PostgreSQL; Cloudary → Cloudinary) for variants the fuzzy rule (≥ 90) misses.
- `link_school` also tries the name without "(…)" and the parenthesised abbreviation ("Học viện … (PTIT)").
- Test isolation: tests no longer load the real KB at app startup; DB test compares `from_db` and `from_csv` on the test database only.
