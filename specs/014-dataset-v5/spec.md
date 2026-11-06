# Feature 014 — Dataset v5

## Why

v4 (feature 013) recovered page-2 jobs of two-column CVs (CV 57: company 0.5 -> 1.0) but, through the
serving path on 19 real test CVs, lost to v3 + 012 on company (0.941 -> 0.788), title and project names.
Diagnosis (counts only, `specs/013-dataset-v4/results.md`):

1. A CV with 5 consecutive jobs of 1 bullet each: v4 kept only the first job. Training data v3 and v4 had
   **0** examples with 4+ jobs of <= 2 bullets.
2. A student CV with projects only: v4 emitted projects as experience. v4 added 184 generated CVs, all with
   jobs; generated data had **0** CVs without a job (no-job share 9.7 % -> 7.7 %).
3. CV 57 dates (v3 and v4): the entry reads company, "<end date> <title>", bullets, start date at the bottom.
   Both models read the top date as the start date and drop the end date. Layout L11 prints the end date
   on its own line *before* the company, so the model never saw this order.

## What

Dataset v5 = dataset v4 (same prompt v3, labels, layout text, held-out splits) plus:

- **many_jobs** — 70 fictional profiles with 4–6 consecutive jobs (1–2 bullets each, non-overlapping
  newest-first dates) and 5–9 projects; layouts L1–L15.
- **student** — 60 fictional profiles with no job and 2–5 projects; layouts L1–L15.
- **L15** — new layout: L11's two-column page with each job as company / "<end date> <title>" / bullets /
  start date; 70 fictional profiles.
- Real training CVs x4 (3 entity swaps) instead of x3.

Variants are derived from the fictional synth_v3 profiles (`training/synth/variants.py`); no real CV data
leaves the machine. Dev holds out a profile together with all its variants.

## Acceptance

- v4 rebuild through the parametrised builder is byte-identical to `data/retrain_v4`.
- Every v5 label value is grounded in its layout text; no generated experience dropped by grounding.
- Train has >= 50 many-short-jobs examples and a no-job share >= 10 %; max length <= 4,096 tokens.
- v5 is adopted only if, through the serving path on the 19 real CVs, company >= 0.90 and skills >= 0.85,
  and CV 57 keeps 3/3 companies with correct start/end dates.
