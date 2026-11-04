# Feature Specification: Retrain Extractor v2 (dataset + Colab notebook)

**Feature Branch**: `006-retrain-v2` (spec directory only)
**Created**: 2026-11-04
**Status**: Draft
**Input**: User: "làm lại dataset và notebook để tôi tiến hành retrain". Evidence from features 003–005 and a label audit (2026-11-04).

## Evidence that motivates the retrain

| Finding | Measured |
|---|---|
| Serving prompt ≠ training prompt | v1 was trained on a 13-rule prompt (~1,040 tokens) + full schema, no `<think>` block; `app/services/prompt.py` serves a different prompt with an empty `<think>` block and a `{` prefill. All feature 003 numbers were measured under this mismatch. |
| Serving prompt asks to summarise | `personal_projects.description: Tóm tắt 2-3 ý` while labels copy bullets verbatim → invented sentences. |
| Truncated training samples | Old format (instruction + schema + CV + label) exceeds 4,096 tokens for 44/395 train samples (max 4,855); the cut part is the end of the JSON (certificates, honours, languages). |
| Loss over the prompt | Old SFT computed loss over the fixed prompt → loss 0.000121 is meaningless. |
| Unstable classification fields | certificates / honours / languages F1 0.85 / 0.74 / 0.83 on val, −7.7 / −8.4 / −4.4 points on val_swap with unchanged labels. |
| Label quality | ≥ 95% of certificate / honour / language labels sit under the matching CV heading; 24 certificate, 19 honour, 6 language, 37 skill and 28 experience-bullet labels are not found in the CV text (ungrounded). |
| Unused data | 95 silver records (clean) are in neither train nor val; no near-duplicate of val (max similarity 41%). |
| Output length | Compact JSON separators cut label length by 12% (mean 1,047 → 918 tokens); serving `MAX_NEW_TOKENS=1500` < longest label (1,727). |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the v2 dataset (P1)
As the developer, I run one command and get train / dev / val / val_swap files ready for Colab, built from the cleaned silver data with the v2 prompt.

1. **Given** `data/clean/silver_dataset.jsonl`, `data/clean/val.jsonl`, `data/val_swap.jsonl`, **When** I run `python -m training.build_dataset`, **Then** `data/retrain_v2/` contains `train.jsonl`, `dev.jsonl`, `val.jsonl`, `val_swap.jsonl` and `summary.json`; val/val_swap keep exactly the 99 CVs and gold labels of feature 003.
2. **Given** a train label item not found in its CV text (certificates, honours, skills, languages, experience bullets), **When** building, **Then** the item is removed from the train label and counted in `summary.json`.
3. **Given** the train pool, **When** building, **Then** each train CV also appears once with company / school / person names swapped (augmentation) and no train text equals a val text.
4. **Given** any record, **When** rendered, **Then** `prompt` equals what serving builds for that CV (same function), and `completion` is compact JSON followed by `<|im_end|>`.
5. **Given** `--hints`, **When** building, **Then** prompts also carry the KB candidate skills found in the CV (variant D); without it, no hints.

### User Story 2 - Train and evaluate on Colab (P1)
1. **Given** the notebook and the dataset folder on Drive, **When** I "Run all" on a T4, **Then** it trains with loss on the answer only, keeps the best checkpoint by dev loss, prints the token-length check (0 truncated samples), evaluates on val and val_swap with the repo's metrics (variant A and B), and exports a Q4_K_M GGUF to Drive.

### User Story 3 - Serve v2 (P2)
1. **Given** `PROMPT_VERSION=v2`, **When** the service extracts a CV, **Then** it uses the v2 prompt (identical to training) and `MAX_NEW_TOKENS` default fits the longest label; with the default `v1`, behaviour is unchanged.

### Edge Cases
- A record longer than the training max length → excluded from train and reported (never silently truncated).
- Labels whose JSON fails to parse → skipped and counted.

## Requirements *(mandatory)*
- **FR-001**: One prompt module (`app/services/prompt_v2.py`) used by both the dataset builder and serving.
- **FR-002**: v2 prompt is short (target < 500 tokens incl. schema), defines certificates / honours / languages by CV heading, and requires verbatim copying (no summarising).
- **FR-003**: Target JSON = full schema (all keys, null / []), compact separators, empty `<think></think>` block in the prompt, never in the trained part.
- **FR-004**: Train labels cleaned of ungrounded items; val / val_swap gold unchanged (comparable with feature 003).
- **FR-005**: Dev split (30 CVs) carved from the train pool for model selection; val is never used for training decisions.
- **FR-006**: Notebook uses `train_on_responses_only`, max length ≥ longest sample, reports truncation = 0.
- **FR-007**: `PROMPT_VERSION` env (`v1` default) switches serving prompt; no API contract change.
- **FR-008**: CV data stays out of git (`ai-service/data/` is ignored); the user uploads the dataset folder to Drive.

## Success Criteria
- **SC-001**: 0 training samples truncated.
- **SC-002**: On val (variant B), certificates / honours / languages F1 each ≥ v1, and the val → val_swap drop on these fields is halved.
- **SC-003**: Entity F1 (company, school) and hallucination rate no worse than v1 (±1 point).
- **SC-004**: Mean output tokens ≥ 10% lower than v1.

## Assumptions
- Variant D (KB hints) is built as an option; serving support for hints is added only if D beats v2 without hints.
- Training is run by the user on Colab T4 (~1 h); Claude prepares and verifies everything locally except GPU training.
