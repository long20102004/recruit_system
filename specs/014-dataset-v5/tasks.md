# Tasks — Feature 014

- [x] T001 Layout L15 in `training/synth/render.py` + tests — *Claude*
- [x] T002 Profile variants (`training/synth/variants.py`: many_jobs, student) + tests — *Claude*
- [x] T003 Parametrise `training/build_dataset_v4.py` (extra generated folders, real swaps, dev by base profile); `training/build_dataset_v5.py`; v4 rebuild byte-identical — *Claude*
- [x] T004 Render 130 variants (L1–L15) + 70 L15 profiles, layout text via `PdfTextDumpRunner`, build `data/retrain_v5/`: train 1,112 (generated 738, silver 250, real 31 + 93 swaps), dev 74, test_real 20; max 3,882 tokens; 0 generated jobs dropped by grounding; 4+ short-job examples 0 -> 65; no-job share 7.7 % -> 12.1 % — *Claude*
- [x] T005 `PROMPT_VERSION=v5` (prompt v3 + `model-v5-q4_k_m.gguf`); notebook `RUN_NAME="v5"` (baseline = v4 notebook numbers); `run_on_colab` can serve v4 — *Claude*
- [ ] T006 User trains v5 on Colab; Claude evaluates through the Colab API (19 real CVs + CV 57) against v3 + 012 and v4 — *user / Claude*
