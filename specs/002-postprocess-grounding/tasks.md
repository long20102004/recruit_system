# Tasks: Post-processing & Grounding (Tier 3)

**Input**: [spec.md](spec.md), [plan.md](plan.md). `[P]` = parallel (different files). Tests use synthetic data only. Claude reviews and re-runs tests before marking `[x]`.

## Phase 1: Setup

- [x] T001 Add `rapidfuzz` to `ai-service/requirements.txt`; add `POSTPROCESS_ENABLED` to `ai-service/app/core/config.py`; create `ai-service/app/postprocess/__init__.py` (placeholder) and `ai-service/tests/postprocess/__init__.py` — *Claude*

## Phase 2: Foundational

- [x] T002 [P] `ai-service/app/postprocess/text_match.py` + `ai-service/tests/postprocess/test_text_match.py` (accent/case, map back to original span, short-name rule, threshold) — *Gemini high*
- [x] T003 [P] [US4] `ai-service/app/postprocess/schema.py` + `ai-service/app/postprocess/skills.py` + `ai-service/tests/postprocess/test_schema_skills.py` — *Free deepseek-v4.1*

## Phase 3: US1 + US2 + US3 (grounding)

- [x] T004 [US1][US2][US3] `ai-service/app/postprocess/grounding.py` + `ai-service/tests/postprocess/test_grounding.py` (depends T002) — *Gemini high*

## Phase 4: US5 + integration

- [x] T005 `ai-service/app/postprocess/pipeline.py`, finalize `__init__.py`, wire into `ai-service/app/api/routes.py` with fallback; `ai-service/tests/postprocess/test_pipeline.py` (end-to-end with the feature-001 hallucination example, disabled flag returns raw, exception fallback, logs counts only, < 100 ms) (depends T003, T004) — *Gemini medium*
- [x] T006 [P] README: post-processing section, `POSTPROCESS_ENABLED` env — *Free mimo*
- [x] T007 Verification: full pytest, real-model smoke with synthetic CV (hallucinated fields removed), diff review — *Claude*

## Order

T001 → (T002 ∥ T003) → T004 → (T005 ∥ T006) → T007
