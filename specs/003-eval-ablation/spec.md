# Feature Specification: Evaluation Harness & Ablation A/B

**Feature Branch**: `003-eval-ablation` (spec directory only)
**Created**: 2026-11-04
**Status**: Draft
**Input**: requirements.md → "Thiết kế thực nghiệm": ablation A (model only) → B (+grounding/type check) → C/D later; measure per-field F1, hallucination rate, latency; validation set shares company/school names with train ("kết quả đẹp giả") → need an independent test set. Backlog item 3 and old `eval_service.py`.

## Context (data facts, verified 2026-11-04)

- Served model = v1 (`checkpoint-250`, `merged_model/model.gguf` identical to Drive `finetune_output/gguf_gguf`), trained on `train.jsonl` (395), validated on `val.jsonl` (99); no overlap. Silver labels by Gemini.
- v2 split (`train_v2`/`val_v2`) overlaps v1 val (76/99 v1-val CVs are in `train_v2`) → each model must be evaluated on its own val.
- Only 9/190 val company mentions are unseen in train; only 7 val CVs have all companies unseen → a natural "unseen" subset is too small.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure A vs B on the validation set (Priority: P1)

As the project team writing Ch2/Ch3, I need one command that runs the served model on the 99 validation CVs and reports per-field quality, hallucination and latency for A (model only) and B (model + post-processing), so we can state the measured value of tier 3.

**Independent Test**: Run the command against a running service; a report with A and B columns is produced; rerunning reuses cached predictions.

**Acceptance Scenarios**:

1. **Given** the service running with post-processing disabled, **When** the evaluation runs, **Then** each CV is extracted once, its raw output stored, and B is computed offline by applying the post-processing function to the same raw output with the same CV text.
2. **Given** an interrupted run, **When** restarted, **Then** already-predicted CVs are skipped.
3. **Given** completed predictions, **When** the report is generated, **Then** it shows per-field precision/recall/F1, hallucination rate, schema validity rate and latency (mean, p50, p95) for A and B, with the sample count.

### User Story 2 - Entity-swapped test set (Priority: P1)

As the team, I need a test variant where company and school names in validation CVs are replaced by fictitious names never seen in training (same replacement in the CV text and the gold labels), so we can show whether the model reads the CV or recalls memorised names.

**Acceptance Scenarios**:

1. **Given** a validation CV and its gold label, **When** the swap is built, **Then** every gold company/school name found in the CV text is replaced consistently in both, using names absent from all training CVs; names not found in the CV text are left unchanged and counted.
2. **Given** the swap set, **When** evaluated, **Then** the report shows A/B metrics for "val" and "val-swap" side by side.
3. **Given** the same seed, **When** rebuilt, **Then** the swap set is identical (reproducible).

### User Story 3 - Trustworthy metric definitions (Priority: P2)

**Acceptance Scenarios**:

1. **Given** predicted and gold profiles, **When** scored, **Then** list fields are compared as sets after accent/case/whitespace normalisation, with entity names (company, school, project name) matched one-to-one at fuzzy ≥ 90, and skills/certificates/honours/languages matched on normalised strings.
2. **Given** a prediction, **When** hallucination is computed, **Then** it is the share of predicted entity values (company, school, project name, email, phone, github_url, certificates, honours) that cannot be found in the CV text by the grounding matcher.
3. **Given** unit tests with hand-made profiles, **When** run, **Then** metrics match hand-computed values.

### Edge Cases

- Model output not parseable → counted as schema-invalid; all its fields score as empty predictions (not skipped).
- Gold list empty and prediction empty → field excluded from micro-averages for that CV (no free credit), but counted in an "empty agreement" rate.
- Service returns 413/5xx → recorded as failure with status; counted as empty prediction.
- Gold label itself contains values absent from the CV (silver noise) → reported as "gold not grounded" count, not hidden.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The harness MUST read a JSONL split with `input` (CV text) and `output` (gold JSON string), default `ai-service/data/val.jsonl`.
- **FR-002**: Predictions MUST be obtained via `POST /api/v1/extract-cv` with the service configured with post-processing disabled; the raw response data and client latency MUST be cached per CV (keyed by a hash of the CV text) under a run directory.
- **FR-003**: B MUST be computed by applying `app.postprocess.postprocess` to A's data with the same CV text.
- **FR-004**: Metrics per field: `personal_info.{full_name,email,phone,github_url}` accuracy (normalised exact; phone by digits), and micro P/R/F1 for `education.school`, `experience.company`, `experience.job_title` (paired with matched company), `personal_projects.name`, `skills`, `certificates`, `honours`, `languages.language`; plus `objective` presence agreement.
- **FR-005**: Hallucination rate per FR US3-2; schema validity rate; latency mean/p50/p95.
- **FR-006**: Entity-swap builder per US2, reproducible by seed, writing `val_swap.jsonl` and a swap summary (counts only).
- **FR-007**: Reports MUST be written as Markdown and JSON in the run directory; console prints the summary table. Reports contain aggregates only; per-CV details stay in the run directory under `ai-service/data/` (git-ignored).
- **FR-008**: The harness MUST NOT require GPU or modify the service; it MUST be runnable as `python -m eval.<command>` from `ai-service/`.
- **FR-009**: Metric functions MUST have unit tests with synthetic data.

### Key Entities

- **Sample**: id (hash), CV text, gold profile.
- **Prediction**: sample id, status, raw data, latency.
- **Run**: directory with predictions cache, per-sample scores, report.

## Success Criteria *(mandatory)*

- **SC-001**: A full run on 99 validation CVs completes unattended and is resumable.
- **SC-002**: The report states A and B for val and val-swap with n, enabling claims like "B reduces hallucination from X% to Y%".
- **SC-003**: Metric unit tests pass and match hand-computed values.
- **SC-004**: No CV content appears in console output or in the Markdown/JSON reports.

## Assumptions

- Silver (Gemini) labels are the reference; they are noisy, so the report also states how many gold values are not grounded in the CV.
- Latency is measured on the current CPU machine (~30–40 s/CV) and labelled as such; GPU latency is out of scope.
- C (KB linking/KG) and D (retrain) are added by later features; the harness keeps a pluggable "variant" step so C can be added without redesign.
- v2 model evaluation is out of scope (served model is v1); the harness accepts any split path so v2 can be evaluated later.
