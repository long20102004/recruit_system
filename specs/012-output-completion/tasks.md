# Tasks: output completion (feature 012)

- [x] T001 [P] [US-A] Continuation pass: `app/services/continuation.py` + wiring in `app/services/generator.py` (GenerationResult gains `continued`), tests `tests/test_continuation.py` — *ChatGPT gpt-6.1-sol*
- [x] T002 [P] [US-B/C] Post-processing: experience-as-project / address-only company, junk skills; `app/postprocess/cleanup.py` + pipeline wiring; tests `tests/postprocess/test_cleanup.py` — *Gemini gemini-3.8-flash-high*
- [x] T003 Measure on 19 real CVs + CV 57 — *Claude*: see results.md (company 0.78 -> 0.94, skills 0.82 -> 0.86; certificates -0.06 accepted). Gemini cleanup: address rule tightened by Claude (kept "Bệnh viện Đa khoa Tỉnh Bình Dương")
