# Tasks: KG Enrichment (Tier 4)

**Input**: [spec.md](spec.md), [plan.md](plan.md), [contracts/extract-cv-v2.md](contracts/extract-cv-v2.md). Claude reviews and re-runs before `[x]`.

## Phase 1: Foundations (parallel)
- [x] T001 [P] `ai-service/app/core/config.py` (+KG_ENABLED, KB_DSN, KB_SEED_DIR), `ai-service/app/kb/store.py`, `ai-service/tests/kb/test_store.py` — *Gemini high*
- [x] T002 [P] [US1-4] `ai-service/app/kg/__init__.py`, `ai-service/app/kg/enrich.py`, `ai-service/tests/kg/__init__.py`, `ai-service/tests/kg/test_enrich.py` (fake KnowledgeBase built in-test) — *Gemini high*
- [x] T003 [P] [FR-008] `backend/src/main/java/recruit/demo/dto/CandidateProfile.java` + `backend/src/test/java/recruit/demo/dto/CandidateProfileJsonTest.java` — *Gemini medium*

## Phase 2: Integration
- [x] T004 `ai-service/app/main.py`, `ai-service/app/api/routes.py` (+ `/health` kb), `ai-service/tests/kg/test_routes_kg.py` — *Gemini medium*
- [x] T005 [US5] `ai-service/eval/variants.py`, `ai-service/eval/metrics.py`, `ai-service/eval/report.py`, tests — *Gemini medium*

## Phase 3: Verify & document
- [x] T006 Run full pytest + `mvn test`; regenerate report with A/B/C from cached predictions; write `results.md` — *Claude*
- [x] T007 Restart services; smoke through backend PDF endpoint — *Claude*
- [x] T008 README (ai-service) KG section + env vars — *Gemini low*
- [x] T009 Commit + push — *Claude*
