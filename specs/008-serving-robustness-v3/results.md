# Results: model v3 + serving robustness (feature 008)

20 real CVs never used for training (`test_real`, gold drafted by Claude, **user review pending**), variant B (post-processing on), GGUF Q4_K_M with llama.cpp exactly as served (greedy).
v1 / v2 rows are the feature 007 baseline (served GGUF, before feature 008).

| Field (F1) | v1 | v2 | v3 raw | **v3 + 008** |
|---|---|---|---|---|
| experience.company | 0.577 | **0.706** | 0.611 | 0.684 |
| education.school | 0.800 | 0.750 | 0.811 | **0.872** |
| skills | 0.604 | 0.533 | 0.718 | **0.741** |
| skills (canonical) | 0.666 | 0.561 | 0.744 | **0.765** |
| experience.job_title | 0.600 | **0.947** | 0.750 | 0.800 |
| personal_projects.name | 0.558 | **0.787** | 0.608 | 0.742 |
| certificates | 0.000 | 0.167 | 0.308 | **0.308** |
| honours | 0.200 | **0.444** | 0.400 | 0.400 |
| languages | **0.800** | 0.351 | 0.710 | 0.688 |
| phone (acc) | 18/18 | 15/18 | – | **18/18** |
| hallucination rate | 1.4 % | **0.8 %** | 1.7 % | 1.5 % |
| usable responses | 20/20 | 20/20 | 18/20 | **20/20** |

**skills_detected** (model ∪ KB scan of the CV text, KB-id level): precision 0.666, recall **0.987**, F1 0.795 — model skills alone: P 0.925, R 0.654, F1 0.767. SC-002 met (R ≥ 0.80, P ≥ 0.6). Lower precision = KB skills mentioned outside the Skills section (projects, experience), still real evidence for Module 2.

**Loop guard**: both degenerate CVs stopped early (1,262 and 351 tokens instead of 2,048; CPU time 135 s and 39 s instead of 221 s and 150 s). The fields after the loop are not generated, so the guard saves time but does not recover them. 0 false positives on 974 gold labels.

**Premature `}`** (found during T004): 2/20 CVs closed the top-level object early; json_repair returned a list of fragments → 502. `merge_fragments` in `app/utils/json_parse.py` puts top-level keys and orphan list items (projects, experience, education) back: both CVs recovered (one with 12 projects).

## Decision (T004)
- Default `PROMPT_VERSION=v3`. v3 + 008 is clearly better on the fields Module 2 relies on (school +0.12, skills +0.21, skills_detected recall 0.99, languages +0.34, phone 18/18) and only slightly below v2 on company (−0.02, < 1 item of 18). Lower on job_title (−0.15) and projects (−0.05). v2 / v1 stay selectable.
- The US4 condition "beats v2 on company" is not met by 0.02; accepted with the reason above.
- Spec 007 SC-001 (company, school, skills ≥ 0.85 and better than v2 everywhere) is **not met**: only school ≥ 0.85.

## For the next retrain
1. Output structure on two-column real layouts: 4/20 CVs degenerate (2 loops, 2 premature `}`), all on long CVs with many projects → more generated CVs with two-column layouts and 6–15 projects.
2. job_title and company on real CVs: error analysis needed (title/company on the same line with dates, interleaved columns).
3. The test set is small (certificates 9 items, honours 5): ±1 item moves these F1 by 0.1–0.2. The gold labels still need the user's review.
4. Eval in the train notebook generates in batches of 8 (left padding), which loops on CVs that do not loop when served one at a time: scores from the notebook are a lower bound; final numbers come from the served GGUF.
