# Tasks: KB (PostgreSQL) & Skill Entity Linking

**Input**: [spec.md](spec.md), [plan.md](plan.md), [contracts/kb-schema.md](contracts/kb-schema.md). Claude reviews and re-runs before `[x]`.

## Phase 1: Setup
- [x] T001 `infra/kb/docker-compose.yml`, `infra/kb/.env.example`, `infra/kb/.gitignore`; add `psycopg[binary]` to `ai-service/requirements.txt` and install; create `ai-service/app/kb/__init__.py`, `ai-service/kb/__init__.py`, `ai-service/tests/kb/__init__.py`; pytest marker `kb_db` — *Claude*

## Phase 2: US1 + foundations (parallel)
- [x] T002 [P] [US1] `ai-service/kb/clean_silver.py` + `ai-service/tests/kb/test_clean_silver.py` — *Gemini medium*
- [x] T003 [P] [US3] `ai-service/app/kb/keys.py`, `ai-service/app/kb/linker.py` + `ai-service/tests/kb/test_linker.py` (CSV fixtures in tmp_path) — *Gemini high*
- [x] T004 [P] [US2] `ai-service/kb/sql/001_schema.sql`, `ai-service/kb/load.py` + `ai-service/tests/kb/test_load.py` (validation logic unit-tested; DB test marked `kb_db`) — *Gemini medium*

## Phase 3: US2 seed
- [x] T005 Run clean_silver on all splits (expect 20 records) — *Claude*
- [x] T006 [US2] `ai-service/kb/build_seed.py` + `ai-service/tests/kb/test_build_seed.py` (depends T003 keys) — *Gemini high*
- [x] T007 [US2] Export canonical skill/school lists; subagent proposes `skill_categories_curated.csv`, `skill_edges_curated.csv`, `university_curated.csv`; Claude spot-checks — *Gemini high + Claude*
- [x] T008 Build seeds, start KB DB, load, integrity checks, run `kb_db` test — *Claude*

## Phase 4: US4 + polish
- [x] T009 [US4] `ai-service/kb/measure.py` + run on cleaned val → `data/runs/kb/linking_report.md`; write `specs/004-kb-skill-linking/results.md` — *Gemini medium + Claude*
- [x] T010 README: KB section (start DB, build/load seeds, linker usage, review workflow) — *Gemini low*
- [x] T011 Full verification + commit — *Claude*

## Order
T001 → (T002 ∥ T003 ∥ T004) → T005 → T006 → T007 → T008 → T009 → T010 → T011
