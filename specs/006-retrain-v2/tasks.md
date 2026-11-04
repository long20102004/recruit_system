# Tasks: Retrain Extractor v2

**Input**: [spec.md](spec.md), [plan.md](plan.md). Claude reviews and re-runs before `[x]`.

## Phase 1: Foundations
- [x] T001 [US1] `ai-service/app/services/prompt_v2.py` — *Claude* (shared contract)
- [x] T002 [P] [US1] `ai-service/app/kb/candidates.py`, `ai-service/tests/kb/test_candidates.py` — *Gemini gemini-3.8-flash-high* (lần 1 không tạo file, giao lại lần 2 đạt)
- [x] T003 [P] [US3] `ai-service/app/core/config.py`, `ai-service/app/services/generator.py`, `ai-service/app/api/routes.py`, `ai-service/tests/test_prompt_version.py`, README env row — *ChatGPT gpt-6.1-terra*; Claude removed an unused import and fixed `tests/test_token_budget.py` patch target

## Phase 2: Dataset + notebook
- [x] T004 [US1] `ai-service/training/build_dataset.py` + label audit — *Claude*
- [x] T005 [US1] `ai-service/tests/training/test_build_dataset.py` — *ChatGPT gpt-6.1-terra*
- [x] T006 [US2] `ai-service/training/retrain_qwen3_v2.ipynb`; local dry-run of scoring cells on gold predictions — *Claude*
- [x] T007 README (ai-service) "Retrain v2" section — *Claude*

## Phase 3: Run (user) + converge
- [ ] T008 User runs the notebook on Colab T4 (`RUN_NAME="v2"`; optionally `"v2_hints"`)
- [ ] T009 Compare with v1 (`report.json`), write `results.md`; if v2 wins, serve GGUF with `PROMPT_VERSION=v2` and re-run `eval_on_colab.ipynb` for llama.cpp numbers — *Claude*
