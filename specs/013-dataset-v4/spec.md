# Feature Specification: Dataset v4 — layout text + layouts for the remaining model gaps

**Created**: 2026-11-05 · **Status**: Clarified
**Input**: User: "Chuẩn bị dataset đi, tôi sẽ tiến hành train v4."

## Why
1. Train/serve mismatch since feature 011: v3 was trained on legacy PDFBox text, the backend now serves column-aware (layout) text.
2. Model-level gaps seen on real CVs (CV 57 and the 19 test CVs): an experience section continued on the next page/column without a heading; skill groups written with parentheses ("AWS (IAM, S3, EC2)", "CI/CD (Jenkins, GitHub Actions)"); certificates with the date on its own line; honours/certificates/languages confusion; projects in a "Present ... Future" timeline with "Description:/Technologies:/Achievements:" prefixes; end date printed above the start date.

## Clarifications
- Label conventions unchanged (v3): skills one item each without group labels (items inside parentheses are separate skills), end_date null for Present, certificates = name as printed, values verbatim.
- Prompt unchanged (`prompt_v3`); the model is served as `PROMPT_VERSION=v4` (prompt v3 + `model-v4-q4_k_m.gguf`).
- Real CVs never leave the machine; only fictional profiles/templates go to subagents.

## Data
| Source | v4 |
|---|---|
| Generated, 10 existing layouts (L1–L10, 2 passes) | same PDFs, text re-extracted with the layout extractor |
| Generated, new layouts L11–L14 (1 pass over the 199 profiles) | new, layout text |
| Real train CVs (31) | source labels re-aligned to the layout text (recovers values the legacy text interleaved), x3 with entity swaps |
| Old synthetic (silver) 250 | unchanged (plain text) |
| test_real | 19 real test CVs (layout text, gold v3) + CV 57 (user's expected JSON) |
| val / val_swap | unchanged (regression) |

### New layouts
- **L11 sidebar-timeline**: left sidebar (education, certificates with date line then name line then a detail line, skills in groups with parentheses, projects in a Present/Future timeline with "Description:/Technologies:/Achievements:" prefixes); right main column = experience with the END date above the START date; page break so that later experiences continue at the top of page 2 with no heading.
- **L12 grouped-skills**: one column; skills rendered as "Group: Head (a, b, c), X, Y" (labels: Head, a, b, c, X, Y).
- **L13 two-column records**: certificates / honours / languages as two-line records (title line, date or score line); languages with a test score.
- **L14 projects-first**: projects before experience, experience heading "Career" / "Quá trình làm việc", education last.

## Success Criteria
- SC-001: 0 generated labels absent from their layout text; every layout renders all 199 profiles (or reports why not).
- SC-002: v4 beats v3 (layout text) on the 19 real CVs and CV 57; no regression > 2 points on val/val_swap.
