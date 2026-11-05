# Tasks: KB from external sources (feature 009)

- [x] T001 [US1] `kb/fetch_sources.py` + snapshots in `kb/sources/` + `MANIFEST.json` (Stack Overflow 2024–2026 `technology.json`, Linguist `languages.yml`, Wikidata entities/SPARQL results, ESCO transversal skills + ICT occupations, Wikipedia university list) — *ChatGPT gpt-6.1-sol*
- [x] T002 [US2] `kb/build_external.py` → `kb/seed/*.csv` with `source` columns + `kb/seed/SOURCES.md`; schema migration `kb/sql/002_source.sql`; `kb/load.py` / `app/kb/store.py` / `app/kb/linker.py` read the new columns — *after T001, ChatGPT gpt-6.1-sol*
- [x] T003 [P] [US3] `app/kb/normalize.py` (replace skills / tech_stack / school with canonical names, dedupe), `include=kg|raw` in `app/api/routes.py`, `KG_ENABLED` default `true`, tests — *Gemini gemini-3.8-flash-high*
- [ ] T004 [US4] Measure link rates old vs new KB and eval with `include=raw`; `results.md`; README / docs — *Claude*: link rates, normalisation check, README, results.md done; API eval with include=raw and PostgreSQL load not run

- [x] T005 Coverage pass 3 (Stack Overflow tags, linker variants, school spelling variants, display names) — *Claude* (ChatGPT passes 1–2 below SC-002)
