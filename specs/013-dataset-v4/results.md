# Feature 013 — v4 results

Model v4 = Qwen3-1.7B + LoRA trained on `data/retrain_v4` (Colab, 224 steps, best dev loss 0.0051; v3: 175 steps, 0.0026).
Served through the Colab API (`run_on`/notebook SERVE cell, llama.cpp GGUF Q4_K_M, serving code incl. feature 012),
`?include=raw`, scored with `eval.report.build_report` variant B — same path as the v3 + 012 baseline (`runs/f012`).
Counts only; no CV content.

## 19 real test CVs (layout text)

| Field | v3 + 012 | v4 + 012 |
|---|---|---|
| experience.company | **0.941** | 0.788 |
| experience.job_title | **0.966** | 0.909 |
| education.school | 1.000 | 1.000 |
| personal_projects.name | **0.882** | 0.822 |
| skills | 0.857 | **0.889** |
| skills_canonical | 0.864 | **0.896** |
| certificates | 0.500 | 0.526 |
| honours | 0.000 | 0.286 |
| languages | 0.750 | **0.815** |
| hallucination | 0 % | 0 % |

The company/project drop comes from 2 CVs: one CV where v4 keeps only the first of 5 consecutive jobs
(the other 4 appear nowhere in the output), one CV where 2 projects are emitted as experience.
No truncation flags on any of the 20 CVs; latency 5–26 s per CV on the Colab GPU.

## CV 57 (two-column DevOps CV, page-2 jobs)

company 0.500 -> **1.000** (VNG and Shopee recovered); certificates 0.286 -> 0.400; languages 1.0 -> 0.0 (1 item).

## Colab in-notebook eval

The notebook's own eval (transformers generate, 2,048-token cap, no continuation/post-processing) reported
certificates 0.0 and company 0.765; through the serving path certificates are 0.526. Use the serving-path numbers.

## Decision

v3 stays the default (`PROMPT_VERSION=v3`): company is the field Module 2 depends on most and v4 loses 3 of 17
correct companies. v4 is available with `PROMPT_VERSION=v4` (`merged_model/model-v4-q4_k_m.gguf`, git-ignored).
