# Results: Ablation A/B (feature 003)

**Date**: 2026-11-04 · **Model**: v1 (`checkpoint-250` → `model.gguf`, Q4_K_M), served on Colab T4 via llama.cpp (CUDA), `temperature=0`
**Splits**: `val` (99 CVs, unseen in v1 training) and `val_swap` (same 99 CVs; 182 company + 96 school names replaced by fictitious names in CV text and gold; 11 three-letter names left unchanged)
**Gold**: silver labels (Gemini); only 0.2% of gold entity values are not found in the CV text.
**Variants**: A = model output; B = A + tier-3 post-processing (feature 002, after the fixes below), applied offline to the same output.

## Main table

| Metric | val A | val B | val_swap A | val_swap B |
|---|---:|---:|---:|---:|
| Schema-valid outputs | 1.000 | 1.000 | 1.000 | 1.000 |
| **Hallucination rate** | **0.032** | **0.002** | **0.041** | **0.002** |
| experience.company F1 | 0.918 | 0.918 | 0.911 | 0.926 |
| education.school F1 | 0.933 | 0.961 | 0.895 | 0.966 |
| personal_projects.name F1 | 0.944 | 0.949 | 0.946 | 0.949 |
| experience.job_title F1 | 0.989 | 0.989 | 1.000 | 1.000 |
| skills F1 | 0.837 | 0.839 | 0.826 | 0.829 |
| certificates F1 | 0.854 | 0.890 | 0.777 | 0.824 |
| honours F1 | 0.743 | 0.768 | 0.659 | 0.693 |
| languages F1 | 0.834 | 0.849 | 0.790 | 0.799 |
| full_name / email / phone / github acc | .98/.98/1.0/.98 | .98/.98/.99/.98 | .98/.99/1.0/.99 | .98/.99/.99/.99 |
| Latency mean / p95 (s, T4 + tunnel) | 16.7 / 20.9 | +<0.1 | 17.1 / 21.0 | +<0.1 |

## Findings

1. **Post-processing (B) removes almost all hallucinated values** (3.2% → 0.2% on val, 4.1% → 0.2% on val_swap) with no loss on entity F1, and improves school/certificates/honours F1 (removed invented items raise precision). Remaining 0.2% equals the gold-noise level.
2. **The model reads names from the CV rather than recalling them**: replacing all company/school names costs only 0.7 pt company F1 and 3.8 pt school F1 for A; B recovers both (0.926 / 0.966 on val_swap).
3. **Classification fields are unstable**: on val_swap, certificates (−7.7 pt), honours (−8.4 pt) and languages (−4.4 pt) drop although their gold labels and the text they come from are unchanged (verified: 0/321 gold items contain a swapped name). No val CV is a near-duplicate of a train CV (nearest-train similarity < 70 for all 99, median 64), so this is not memorisation of whole CVs. Same direction: CPU vs GPU inference of the same GGUF gives identical output for only 2/24 CVs, and certificates/honours/languages F1 on those 24 CVs is 0.67/0.71/0.68 (CPU) vs 0.81/0.83/0.84 (GPU).
4. **Skills F1 ≈ 0.83–0.84** in all settings; post-processing barely changes it (only label stripping/dedupe). Gains need entity linking / KB (feature 004–005, variant C).
5. **Latency** ~17 s/CV on T4 (≈1,100–2,500 prompt tokens + up to ~1,000 output tokens), ~90 s/CV on local CPU — far from the 1–2 s target.

## Bugs found and fixed during evaluation (feature 002 code)

- `find_span` matched short names inside other words ("TMA" in "hotmail"/"Postman") and widened them, replacing correct companies (3 TP lost on val). Fix: exact match must be a whole word; names < 6 characters never match partially.
- Contact grounding nulled GitHub URLs that the PDF text breaks across lines. Fix: email/GitHub containment ignores whitespace.
- Before the fixes, B lowered val company F1 (0.918 → 0.903); after, no regression. Regression tests added.

## Recommendation on re-building the dataset / retraining

- **Not needed for entity extraction** (names, contacts, education, projects): F1 0.92–0.97 with B, robust to unseen names.
- **Needed for certificates / honours / languages** (and latency): instability under irrelevant input changes points to weak label definitions in the silver data and the long 13-rule prompt. Retrain once, after feature 004, combining: cleaned labels (incl. the 20 records with group labels in skills), clearer certificate/honour/language definitions, short prompt + `train_on_responses_only` + empty `<think>` block in both train and serve, entity-swap augmentation, KB `candidate_skills` hints (variant D), and inputs produced by the same PDFBox extraction used in serving.

## Limitations

- n = 99 per split; differences < ~2 pt are within noise. Gold is silver (Gemini), not human-verified.
- 3-letter company names were not swapped. Latency includes Cloudflare tunnel overhead.
- Variant C (KB linking/KG) and D (retrain) pending features 004–005.

Reproduce: see [plan.md](plan.md) → Usage; run dir `ai-service/data/runs/v1_gpu` (git-ignored).
