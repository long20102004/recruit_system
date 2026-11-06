# Baseline on the locked real test set (20 CVs, gold v3 drafted by Claude, review pending)

Variant B (post-processing on), same gold and scorer. v1: llama.cpp CPU (local); v2: llama.cpp GPU (Colab T4), 2 CVs re-run on CPU after empty GPU outputs.

| Field | v1 F1 (tp/fp/fn) | v2 F1 (tp/fp/fn) |
|---|---|---|
| experience.company | 0.577 (15/19/3) | **0.706** (12/4/6) |
| experience.job_title | 0.600 (6/1/7) | **0.947** (9/0/1) |
| education.school | **0.800** (16/4/4) | 0.750 (15/5/5) |
| personal_projects.name | 0.558 (24/10/28) | **0.787** (35/2/17) |
| skills | **0.604** (182/59/180) | 0.533 (154/62/208) |
| skills (canonical KB ids) | **0.666** | 0.561 |
| certificates | 0.000 (0 predicted / 9 gold) | **0.167** (1/2/8) |
| honours | 0.200 (1/4/4) | **0.444** (2/2/3) |
| languages | **0.800** (12/4/2) | 0.351 (13/47/1) |
| name / email | 16/18, 19/19 | 16/18, 19/19 |
| phone / github | **18/18**, **10/12** | 15/18, 8/12 |
| hallucination rate | 1.4 % | **0.8 %** |
| latency | 63.8 s (CPU) | 9.6 s (GPU; ~43 s CPU on cv01) |

Reading: v2 is better on structure (company, title, projects, honours); v1 is better on lists and contacts (skills, languages, phone) — v1 was trained on ~48 real CVs, v2 almost only on synthetic ones; v2's languages errors come from the v2 prompt rule. Neither model reaches SC-001 (≥ 0.85 on company, school, skills). v3 target: beat the better of v1/v2 on every field.
