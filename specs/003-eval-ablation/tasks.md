# Tasks: Evaluation Harness & Ablation A/B

**Input**: [spec.md](spec.md), [plan.md](plan.md). Synthetic data in tests only. Claude reviews and re-runs before `[x]`.

## Phase 1: Setup
- [x] T001 Gitignore `ai-service/data/`; download `train.jsonl`, `val.jsonl` (+v2 files) into it; verify model/split mapping — *Claude*
- [x] T002 Create `ai-service/eval/__init__.py`, `ai-service/tests/eval/__init__.py` — *Claude*

## Phase 2: Core (parallel, different files)
- [x] T003 [P] [US3] `ai-service/eval/dataset.py`, `ai-service/eval/metrics.py`, `ai-service/tests/eval/test_metrics.py` — *Gemini high*
- [x] T004 [P] [US2] `ai-service/eval/swap.py`, `ai-service/tests/eval/test_swap.py` — *Gemini medium* (uses `eval.dataset.Sample` interface from plan; defines its own loader if dataset.py absent)
- [x] T005 [P] [US1] `ai-service/eval/predict.py`, `ai-service/eval/variants.py`, `ai-service/eval/report.py`, `ai-service/tests/eval/test_predict_report.py` (fake HTTP server or monkeypatched urlopen) — *Gemini medium*

## Phase 3: Run & results
- [x] T006 Build `data/val_swap.jsonl`; start service with `POSTPROCESS_ENABLED=false`; run predictions for val and val_swap in background — *Claude*
- [x] T007 Generate report; review numbers for sanity; write `specs/003-eval-ablation/results.md` (aggregates only) — *Claude*
- [x] T008 README section "Đánh giá (evaluation)" in `ai-service/README.md` — *Gemini low*

## Order
T001 → T002 → (T003 ∥ T004 ∥ T005) → T006 → T007 ∥ T008
