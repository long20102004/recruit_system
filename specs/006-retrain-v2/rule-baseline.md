# Rule-based baseline vs LLM v1 (2026-11-04)

**Question**: can the backend rule-based pipeline (`/api/v1/cv/extract-rule-based`) replace the fine-tuned LLM?

**Method**: each CV text of val / val_swap (99 + 99) is rendered to a PDF (PDFBox, Liberation Sans; heading-like lines bold 13 pt; markdown markers removed) and passed to `RuleBasedCvExtractionService` via `backend/src/test/.../RuleBasedEvalRunner.java`. Scored with the feature 003 harness (`eval.report`, variant B) against the same gold as LLM v1 (Colab T4, variant B).

| Field (F1 / accuracy) | Rule val | LLM v1 val | Rule val_swap | LLM v1 val_swap |
|---|---:|---:|---:|---:|
| full_name | 0.960 | 0.980 | 0.960 | 0.980 |
| email | 0.970 | 0.980 | 0.970 | 0.990 |
| phone | 0.418 | 0.990 | 0.418 | 0.990 |
| github_url | 0.938 | 0.979 | 0.938 | 0.990 |
| education.school | 0.675 | 0.961 | 0.670 | 0.966 |
| experience.company | 0.103 | 0.918 | 0.551 | 0.926 |
| personal_projects.name | 0.525 | 0.949 | 0.521 | 0.949 |
| skills | 0.710 | 0.839 | 0.700 | 0.829 |
| certificates | 0.760 | 0.890 | 0.744 | 0.824 |
| honours | 0.625 | 0.768 | 0.625 | 0.693 |
| languages.language | 0.726 | 0.849 | 0.727 | 0.799 |
| hallucination rate | 0.000 | 0.002 | 0.000 | 0.002 |
| time / CV | ~9 ms (CPU) | ~17 s (T4) | | |

## Reading
- Rules are ~1,800× faster and never invent values, but lose 10–80 F1 points on everything except name / email / GitHub.
- Main failure is **structure**: the same experience line is written as "Title, Company, Date", "Company | Title | Date", "Title - Company (Date)"; rules cannot tell which part is the company (company F1 0.10). val_swap scores higher on company only because swapped names start with "Công ty …".
- Phone 0.42 is mostly a data artefact: 53 of the 57 missed val phones have 9 digits (e.g. "081057438"), which is not a valid Vietnamese number, so the regex rightly rejects them; on valid numbers the rules find 41/44. The regex was still widened for real formats ("(+84) 912 345 678", "(0377) 386 391", "-" separators), with tests.
- Conclusion: rules cannot replace the LLM. They fit as a fast path only for contact fields and, after fixes, as a pre-check; the LLM stays for structure. Section-based fields (certificates / honours / languages) reach 0.63–0.76 with rules, so a hybrid (rule section split + LLM) is worth testing only after v2.

## Bug found and fixed
`CandidateProfile.parseListStringSafely` returned immutable lists (`toList()` / `List.of`), so the rule-based extractor and validator threw `UnsupportedOperationException` on 119/198 CVs (bug since the initial commit). It now returns `ArrayList`; regression test `CandidateProfileJsonTest.descriptionListsStayMutable`.

## Privacy fix (same day)
Backend logs no longer contain CV values: PDF file names removed from `CvAnalysisService` logs; rule-based validation warnings (emails, URLs, company / school names) and unknown headings are logged as counts only.
