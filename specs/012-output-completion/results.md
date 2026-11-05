# Results: output completion + cleanup (feature 012), with the extractor fixes of feature 013

Model v3, layout text, 19 real test CVs (same CVs as feature 011), variant B.

| Field (F1) | 011 (layout text) | **011 + 012** |
|---|---:|---:|
| company | 0.780 | **0.941** |
| job_title | 0.929 | **0.966** |
| school | 1.000 | 1.000 |
| project name | 0.860 | **0.882** |
| skills | 0.822 | **0.857** |
| skills (canonical) | 0.832 | **0.864** |
| certificates | 0.556 | 0.500 |
| honours | 0.000 | 0.000 |
| languages | 0.759 | 0.750 |
| hallucination rate | 0.7 % | **0.0 %** |

- Continuation recovered CV 05 (object closed after projects: 17 skills back); CV 01 (loop guard, long string) still loses 15 skills.
- Certificates: 2 extra certificates (grounded in the CV text, absent from the draft gold) on 2 CVs; the field has 9 gold items, so 1–2 items move F1 by ~0.05. SC-001 "no field drops > 0.01" is missed on this field; accepted for company +0.16, skills +0.035, hallucination 0.
- CV 57 unchanged: experiences continued on page 2 (VNG, Shopee) still missing — the target of dataset v4 (feature 013).
