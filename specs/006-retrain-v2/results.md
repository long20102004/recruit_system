# Results: Retrain v2 (feature 006)

**Date**: 2026-11-05 · Colab T4 · `training/retrain_qwen3_v2.ipynb` (`RUN_NAME="v2"`), code at 03ca84e.
Training: 824 samples × 2 epochs = 206 steps; 0 samples truncated (max 3,723 tokens); loss on the JSON only (1,493 / 3,455 tokens of the first sample); best dev loss 0.00357 at step 175 (kept).
Evaluation: HF 4-bit generation, batch 8, greedy; scored with the feature 003 harness. v1 = feature 003 Colab run (llama.cpp GGUF), variant B.

| Field (variant B) | v1 val | **v2 val** | v1 val_swap | **v2 val_swap** |
|---|---:|---:|---:|---:|
| experience.company F1 | 0.918 | **0.995** | 0.926 | **0.995** |
| education.school F1 | 0.961 | **1.000** | 0.966 | **0.995** |
| personal_projects.name F1 | 0.949 | **0.982** | 0.949 | **0.982** |
| skills F1 | 0.839 | **0.932** | 0.829 | **0.928** |
| skills canonical F1 | 0.855 | **0.938** | 0.845 | **0.935** |
| certificates F1 | 0.890 | **0.958** | 0.824 | **0.976** |
| honours F1 | 0.768 | **0.981** | 0.693 | **0.981** |
| languages F1 | 0.849 | **0.972** | 0.799 | **0.981** |
| hallucination rate | 0.002 | 0.002 | 0.002 | 0.002 |
| valid JSON | 99/99 | 99/99 | 99/99 | 98/99 |

Mean generated tokens: 973; 1/198 outputs hit the 2,048-token cap.

## Success criteria
- SC-001 0 truncated samples: **met**.
- SC-002 certificates / honours / languages ≥ v1 and val → val_swap drop halved: **met** (+7 to +29 points; no drop at all on swap).
- SC-003 entities and hallucination not worse: **met** (company +7.7, school +3.9; hallucination equal).
- SC-004 ≥ 10% fewer output tokens: **not yet verified** — needs the same counter for v1 and v2 on llama.cpp.

## Caveats
- Gold labels are silver (Gemini) and val is mostly synthetic CVs with clean headings, the same distribution as train; numbers above 0.95 mostly show v2 learned the label conventions. The real-CV test set (1 CV so far) is the check that matters.
- v1 numbers were measured under the train/serve prompt mismatch, so part of the gain comes from fixing that mismatch, not from the retrain itself.
- Latency in the notebook (≈18 s/CV) is batch time / 8 on HF 4-bit and is not comparable with serving; serving latency must be measured with the GGUF on llama.cpp.
- 1 invalid JSON on val_swap and 1 cap hit: inspect before serving.

## Real CV (1 CV, served end-to-end: backend PDF → ai-service llama.cpp CPU, variant C)
| | v1 | v2 |
|---|---|---|
| Latency (CPU, same machine) | 114.5 s | **43.1 s** (1,198 prompt + 759 output tokens) |
| Contacts, school, company, project names, languages | all correct | all correct |
| Honours | 1/2 (spacing changed) | **2/2** verbatim |
| Dates | rewritten to ISO ("2025-10-01") | **verbatim** ("October 2025") |
| Job title (CV gives none) | invented "Backend Developer" (now nulled by post-processing) | **null** |
| Skills | invented "Python" (now removed by post-processing) | none invented |
| Project role | correct | list `["Developer"]` → fixed in post-processing (joined) |
| Project tech_stack | 8 / 10 items | 8 / **0** (key omitted for "Tech: Backend(…), Database(…)" layout) |

v2 GGUF: Drive `finetune_output_v2/gguf_gguf/Qwen3-1.7B.Q4_K_M.gguf`, served locally as `merged_model/model-v2-q4_k_m.gguf` with `PROMPT_VERSION=v2`.

## Next
1. ~~Serve v2 locally and run the real CV~~ (done, above). Grow the real-CV set to 30–50 CVs; watch tech_stack on unusual layouts.
2. Re-run `eval_on_colab.ipynb` with the v2 GGUF for llama.cpp numbers (SC-004, latency).
3. Variant D (KB hints): low expected gain now that v2 is at 0.93–1.00 on val; skip unless the real-CV set shows skill-spelling problems.
