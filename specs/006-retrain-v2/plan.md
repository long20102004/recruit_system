# Implementation Plan: Retrain Extractor v2

**Spec**: [spec.md](spec.md) | **Date**: 2026-11-04

## Summary

One prompt module (`app/services/prompt_v2.py`) renders both training samples and serving prompts. A builder (`training/build_dataset.py`) turns the cleaned silver data into rendered train / dev / val / val_swap files. A Colab notebook (`training/retrain_qwen3_v2.ipynb`) trains with loss on the answer only, evaluates with the feature 003 harness, and exports GGUF. Serving selects the prompt via `PROMPT_VERSION`.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Minimal Scope | PASS | No API change; v1 remains the default |
| II. Contracts | PASS | `POST /api/v1/extract-cv` unchanged; `/health` gains `prompt_version` (additive) |
| III. Verification | PASS | Unit tests; local dry-run of the notebook's scoring on gold predictions; GPU training run by the user |
| IV. CV Data Security | PASS | CV data stays in `ai-service/data/` (git-ignored) and the user's Drive; `summary.json` has counts only |
| V. Maintainable | PASS | Prompt in one place; builder reuses grounding, swap and eval code |

## Design

```text
ai-service/
├── app/services/prompt_v2.py   # SYSTEM_PROMPT, render_prompt(cv, hints?), render_target(profile)
├── app/core/config.py          # PROMPT_VERSION (v1|v2); MAX_NEW_TOKENS default 1500 (v1) / 2048 (v2)
├── app/services/generator.py   # build_prompt() picks v1 or v2
├── app/kb/candidates.py        # CandidateSkillFinder (variant D hints)
└── training/
    ├── build_dataset.py        # python -m training.build_dataset [--hints]
    └── retrain_qwen3_v2.ipynb  # Colab T4
```

### Prompt format (train == serve)
```
<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{cv}[\n\n{hints}]<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
```
Target: compact full-schema JSON + `<|im_end|>`. `train_on_responses_only` masks everything up to the empty think block, so the loss covers the JSON and the stop token only.

### Data
- Pool: `data/clean/silver_dataset.jsonl` minus any val / val_swap text → 442 CVs; 30 → dev, 412 → train.
- Train labels: drop items not found in the CV (same `contains` grounding as serving): skills, certificates, honours, languages, experience bullets, project tech_stack.
- Augmentation: `eval.swap.build_swap` on train (company / school names), avoiding val_swap names.
- Val / val_swap: feature 003 files, gold untouched.

### Training (notebook defaults)
LoRA r=16, alpha=32, all attention + MLP projections; lr 2e-4 cosine, warmup 5%; batch 2 × grad-accum 4; 2 epochs; eval / save every 25 steps; best by dev loss; max length 4,096 (asserted ≥ longest sample).

### Evaluation
Batched greedy generation (HF, 4-bit) on val + val_swap → `predictions.jsonl` in the `eval.predict` format → `eval.report.build_report` (A / B / C) → table vs v1 (variant B). Final serving numbers (llama.cpp GGUF, latency) come from `eval_on_colab.ipynb` with `PROMPT_VERSION=v2`.

## Risks
- Unsloth / TRL API drift on Colab: the notebook tries both `max_length` / `max_seq_length` and `processing_class` / `tokenizer`; a mask assertion fails fast if response masking is wrong.
- HF 4-bit output can differ from GGUF Q4_K_M output (seen in 003: CPU vs GPU); notebook numbers are a gate, not the final report.
