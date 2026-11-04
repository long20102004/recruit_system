# Findings from the first real CV (2026-11-04)

Independent test set started at `ai-service/data/real_test/` (git-ignored, CV data): 1 real CV (PDF → backend PDFBox text), gold labelled by Claude from the PDF with the silver conventions, to be reviewed by the owner. One CV is an anecdote, not a measurement; target 30–50.

## Result on the real CV (model v1, CPU, served pipeline)
| | LLM v1 | Rule-based |
|---|---|---|
| Contact fields | 4/4 | 4/4 |
| School / company / project names | 1/1, 1/1, 2/2 | 1/1, 1 + 1 fp, 0/2 |
| Honours / languages | 1 exact + 1 spacing variant / 1 | 1 + 2 fp / 1 |
| Time | 114 s (CPU) | 0.13 s |

Model v1 problems seen: invented job title "Backend Developer" (CV gives none; phrase occurs in the objective), invented skill "Python", dates rewritten to ISO ("2025-10-01").

## Post-processing gaps found and fixed (feature 002 amended)
1. Skills were never grounded → ungrounded skills now removed (whitespace-insensitive match, so "Spring Boot (…)" vs "Spring Boot(…)" is kept).
2. Empty job title removed the whole experience (spec 002 US3) → title is now nulled instead; student titles still remove.
3. Job title only had to appear anywhere in the CV → must appear within 200 / 300 characters around the company.
4. KB `link_school` did not handle "… - PTIT" → first part and single-token last part are tried; a multi-word last part (parent university, "… - ĐHQG TP.HCM") is never used.

## Effect on val / val_swap (v1 GPU predictions, variant B)
| Field | before val | after val | before swap | after swap |
|---|---:|---:|---:|---:|
| skills F1 | 0.843 | 0.855 | 0.829 | 0.844 |
| skills canonical F1 | 0.855 | 0.865 | 0.845 | 0.859 |
| job_title F1 (fp) | 0.989 (2) | 0.992 (0) | 1.000 (0) | 0.992 (0) |
| other fields | unchanged | | | |

Trade-off: one correct title per split is now nulled — a 2-column PDF where the headline title sits ~800 characters from the company.
