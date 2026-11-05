# Tasks: dataset v4 (feature 013)

- [x] T001 [P] Layouts L11–L14 in `training/synth/render.py` (+ `--layouts`, `--pdf-only` options), tests — *ChatGPT gpt-6.1-sol*; Claude: L13 gutter widened (spacer column)
- [x] T002 [P] Re-align real train labels to layout text; `training/build_dataset_v4.py`; `PROMPT_VERSION=v4` (prompt v3 + model-v4 GGUF); notebook `RUN_NAME="v4"` — *Claude*
- [x] T003 Render L11–L14, extract layout text, build `data/retrain_v4/`, checks (labels in text, token lengths) — *Claude*: train 895 (generated 552 over L1–L14, silver 250, real 31 + 62 swaps), dev 60, test_real 20 (19 + CV 57); max 3,882 tokens; prompt parity 0/1,074; no leakage. Extractor fixes found while building: glyph/text alignment (split-word glitches), narrow date strip after its paragraph, line-break hyphenation in matching; generated label drops 235 -> 90 on L1–L10
- [ ] T004 User trains v4 on Colab; Claude evaluates (19 real CVs + CV 57 + val) — *user / Claude*
