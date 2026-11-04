# Implementation Plan: Evaluation Harness & Ablation A/B

**Branch**: `003-eval-ablation` (spec dir only) | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Offline evaluation package `ai-service/eval/` (not imported by the service): dataset loading, entity-swap builder, HTTP prediction runner with cache/resume, metrics (field P/R/F1, hallucination, latency) and Markdown/JSON report comparing variants A (raw) and B (`postprocess`). Data and runs live in git-ignored `ai-service/data/`.

## Technical Context

**Language**: Python 3.14 venv; **Deps**: stdlib (`urllib.request`, `json`, `hashlib`, `statistics`, `argparse`, `random`), `rapidfuzz` (already), reuse `app.postprocess` and `app.postprocess.text_match`. No new dependencies.
**Testing**: pytest unit tests for metrics/swap/dataset with synthetic data (`tests/eval/`).
**Runtime**: ~99 × 35 s ≈ 1 h per split on CPU → run in background, resumable.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Minimal Scope | PASS | New package only; service untouched |
| II. Contracts | PASS | Uses existing endpoint |
| III. Verification | PASS | Unit tests + one real run |
| IV. CV Data Security | PASS | Data git-ignored; reports aggregate-only; console prints no content |
| V. Maintainable | PASS | Small modules, CLI entry points |

## Design

```text
ai-service/eval/
├── __init__.py
├── dataset.py     # load_split(path) -> list[Sample]; Sample(id, cv_text, gold: dict)
├── swap.py        # build_swap(samples, train_samples, seed) -> (list[Sample], summary); CLI: python -m eval.swap
├── predict.py     # run_predictions(samples, base_url, run_dir, timeout) ; CLI: python -m eval.predict
├── metrics.py     # score_sample(pred, gold, cv_text) -> dict ; aggregate(scores) -> dict
├── variants.py    # VARIANTS = {"A": identity, "B": lambda data, cv: postprocess(data, cv)[0]}
└── report.py      # build_report(run_dir, splits) -> md/json ; CLI: python -m eval.report
```

- **Sample.id** = sha1(cv_text)[:12]. `gold` = `normalize_profile(json.loads(output))` (from `app.postprocess.schema`) so gold and predictions share a schema.
- **predict.py**: for each sample not in `run_dir/predictions.jsonl`, POST `{"cv_text": ...}`, record `{id, status, data|None, latency_s}`; append line immediately (resume). Print progress as `i/n id status latency` only.
- **metrics.py**:
  - `norm` = `text_match.normalize`.
  - Scalars: accuracy over samples where gold non-null (plus counts of pred-non-null when gold null = false positives).
  - Entity lists (school, company, project name): greedy one-to-one matching by `rapidfuzz.fuzz.token_set_ratio(norm(a), norm(b)) >= 90`; TP/FP/FN.
  - job_title: for matched company pairs, correct if `norm` equal or ratio ≥ 90.
  - Set lists (skills, certificates, honours, languages.language): set of `norm` strings.
  - Hallucination: for predicted entities (company, school, project name, email, phone(digits), github_url, certificates, honours) count `find_span is None` (contacts: `contains`/digits rule as in grounding); rate = ungrounded / total predicted.
  - Gold-not-grounded: same check on gold values (silver noise indicator).
  - Invalid/failed predictions → empty profile, flagged.
  - `aggregate`: micro P/R/F1 per field, hallucination rate, schema-valid rate, failure rate, latency mean/p50/p95, n.
- **swap.py**: collect train entity names (normalised) from `train.jsonl` gold; fictitious name generator from fixed word pools (company: prefix "Công ty TNHH"/"Công ty Cổ phần" + two invented syllable words + suffix "Tech"/"Solutions"/"Software"; school: "Trường Đại học" + invented place-name), seeded `random.Random(seed)`, rejecting names whose `norm` appears in train names or the CV. For each val sample: for each gold company/school, locate all occurrences in CV via normalized-with-map exact containment (`text_match.normalize_with_map`) and replace original spans (right-to-left); replace the gold value with the new name. Not found → unchanged, counted. Same original name → same fictitious name within a CV. Write `data/val_swap.jsonl` (same `instruction/input/output` format) + `data/val_swap.summary.json` (counts only).
- **report.py**: for each split (`val`, `val_swap`) and variant (A, B): score all samples, aggregate, write `run_dir/report.md`, `report.json`, `scores.jsonl`; console prints the Markdown summary table.

## Usage

```bash
cd ai-service
python -m eval.swap --val data/val.jsonl --train data/train.jsonl --out data/val_swap.jsonl --seed 42
POSTPROCESS_ENABLED=false python main.py &                       # service, post-processing off
python -m eval.predict --split data/val.jsonl      --run data/runs/v1 --base-url http://localhost:8000
python -m eval.predict --split data/val_swap.jsonl --run data/runs/v1 --base-url http://localhost:8000
python -m eval.report  --run data/runs/v1 --splits data/val.jsonl data/val_swap.jsonl
```

Predictions are keyed by CV hash, so both splits share one `predictions.jsonl`.

## Subagent Assignment

| Task | Model |
|---|---|
| dataset.py + metrics.py + tests | agy `gemini-3.8-flash-high` (metric correctness) |
| swap.py + tests | agy `gemini-3.8-flash-medium` |
| predict.py + variants.py + report.py + tests | agy `gemini-3.8-flash-medium` (free tier exhausted) |
| Real run (~2 h CPU), review, results write-up | Claude |
