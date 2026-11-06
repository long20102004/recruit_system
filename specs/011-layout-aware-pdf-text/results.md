# Results: layout-aware PDF text (feature 011)

Model v3 (GGUF, llama.cpp CPU, serving code incl. features 008/011 post-processing), 19 real test CVs
(gold drafted on the legacy text, so the comparison is biased toward legacy), variant B.

| Field (F1) | legacy text | **layout text** |
|---|---:|---:|
| company | 0.667 | **0.780** |
| job_title | 0.800 | **0.929** |
| school | 0.865 | **1.000** |
| project name | 0.729 | **0.860** |
| skills | 0.737 | **0.822** |
| skills (canonical) | 0.740 | **0.832** |
| certificates | 0.308 | **0.556** |
| honours | 0.000 | 0.000 |
| languages | 0.667 | **0.759** |
| hallucination rate | 1.6 % | **0.7 %** |
| phone / email / name | 17/17, 18/18, 15/17 | same |

19/19 valid JSON; 2 outputs still cut by the loop guard.

CV 57 (two-column DevOps CV, gold = the user's expected JSON): school, first company, title, dates,
7 bullets and both project names now correct (legacy: school mixed with the company, company "TOIEC").
Still missing: the 2 experiences continued on page 2 without a section heading, items inside skill
groups ("AWS (IAM, S3, ...)"), 2 certificates — model-level gaps for a future dataset v4.

Decision: `cv.pdf.text-mode=layout` is the default (commit 5ab51dc); dataset v4 / retraining not needed now.
