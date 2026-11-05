# Tasks: Dataset v3

- [x] T001 Lock the real test set: 19 real CVs in no training data + cv01 → `data/real_test/test_v3.jsonl`; gold drafted by Claude on PDFBox text (`data/real_test/gold_v3/`) — **user review pending**. CV 46 (Japanese, non-IT) excluded.
- [x] T002 v2 baseline on the test set (company 0.706, school 0.75, skills 0.533, languages 0.351, certificates 0.167) — *Claude*
- [x] T003 Real CVs for training: `training/real_align.py` (snap to PDFBox text, date respelling, location stripping, programming languages out of `languages`) → 31 CVs — *Claude*
- [x] T004 199 fictional profiles (junior 50, middle 60, senior 60, lead 29): Gemini b01/b03/b05/b07/b09 accepted first time; ChatGPT b02/b04/b06/b08/b10 rejected (script-generated templates, sequential phones) and redone with an automatic diversity check — *Gemini gemini-3.8-flash-high ∥ ChatGPT gpt-6.1-terra*
- [x] T005 `training/synth/render.py`: 10 layouts → LibreOffice PDF → backend PDFBox text; `--layout-offset` for a second pass — *ChatGPT gpt-6.1-sol*; offset option by Claude
- [x] T006 `app/services/prompt_v3.py`, `PROMPT_VERSION=v3`, `training/build_dataset_v3.py` (train 711, dev 45, val/val_swap, test_real 20; max 3,869 tokens) — *Claude*
- [x] T007 Train notebook: `RUN_NAME="v3"`, scores `test_real` and prints the v2 comparison — *Claude*
- [x] T008 User trains v3 on Colab (2026-11-05)
- [x] T009 Compare v1 / v2 / v3 on the real test set — *Claude*: SC-001 not met (only school ≥ 0.85); v3 served by default with feature 008, see ../008-serving-robustness-v3/results.md
