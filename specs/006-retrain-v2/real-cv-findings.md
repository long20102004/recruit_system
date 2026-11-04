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

## Real-CV batch on Colab GPU (2026-11-05, model v2)
`dataset/` (user-provided, git-ignored): 56 PDFs + 30 images. 54 PDFs have a text layer (2 scans), 1 duplicate (08≈25), 1 seen in v2 train (53) → 53 CVs sent to the v2 service on Colab T4 via Cloudflare tunnel.

- Latency on T4: mean 7.6–9.7 s / CV (p95 15–17 s); valid response 53/53.
- **4/53 empty profiles with HTTP 200**: model output not parseable → `json_repair` + schema completion return an empty profile silently. 3 of them are fine on CPU (same model, same text) → GPU-run issue; 1 is a placeholder CV ("EXAMPLE").
- Gold available for 13 CVs (12 matched to val / v1-train labels by text similarity ≥ 97–100 %, + cv01). Variant B, GPU failures replaced by the CPU rerun:

| Field | F1 / acc (tp/fp/fn) |
|---|---|
| name / email | 13/13, 13/13 |
| phone / github | 11/12, 7/9 |
| experience.company | 0.733 (11/3/5) |
| experience.job_title | 1.000 (10/0/0) |
| education.school | 0.846 (11/2/2) |
| personal_projects.name | 0.897 (35/0/8) |
| skills | 0.706 (133/20/91) |
| skills canonical | 0.756 |
| certificates | 0.000 (0/4/5) |
| honours | 0.154 (2/10/12) |
| languages | 0.417 (5/8/6) |
| hallucination rate | 0.0 (gold set), 0.8 % (40 unlabelled CVs) |

Reading:
- Borrowed gold is noisy for exact-string fields: v1-train labels were made on a different text extraction ("English B1 (2024)" in the label vs "English B1 2024" in the PDFBox text) — certificates / honours numbers understate the model.
- Real model errors: programming languages under a "Languages:" sub-heading of the skills section are output as spoken languages (CVs 21, 52) — the v2 prompt rule "mục Languages → languages" causes this; grouped skill lines ("Languages: Csharp, …", "ORM: …") are mostly skipped (CV 14: 3 of 31 skills); school names output as honours (CV 15); company names glued to the next token ("… 6/2025", "Datacenter NHÂN VIÊN …").
- Conclusion: on real CVs v2 is far below its val scores (0.93–1.00); v2 was trained almost only on synthetic CVs.
