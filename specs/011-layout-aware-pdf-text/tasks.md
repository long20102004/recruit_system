# Tasks: Layout-aware PDF text (feature 011)

- [x] T001 [US1] Backend: recursive XY-cut reading order in `extraction/pdf/PdfTextExtractor.java` (FR-1..3), `cv.pdf.text-mode` switch in `CvAnalysisService` (FR-4), synthetic-PDF tests — *ChatGPT gpt-6.1-sol* (2 passes: XY-cut, then PDFBox word runs instead of guessed spaces); Claude: column rule uses side extent (>= 25 %), split runs at large intra-run glyph gaps (PDFBox merged glyphs of two columns into one word)
- [x] T002 [P] [US1] ai-service: skill list split keeps parenthesised groups (FR-5) + tests — *Claude*
- [x] T003 [US1] Measure on the 56 real PDFs (contiguity of gold strings, one- vs two-column), tune thresholds — *Claude*: two-column CV 57 now read column by column; labelled real CVs contiguity old 99 % / new 91 % (labels were aligned to the old text, biased); synthetic layouts 100 % / 99 %
- [x] T004 [US1] Run v3 on two-column real CVs with new vs legacy text, score; decide the default text mode; DevOps CV check when the PDF is available — *Claude*: CV 57 company 0 -> 0.5, title 0 -> 1.0, school correct; page-2 experiences (no heading) still missed by the model; 19 real CVs: every field better than legacy (company 0.667 -> 0.780, school 0.865 -> 1.000, skills 0.737 -> 0.822), see results.md; layout made the default

- [x] T005 Post-processing swaps start/end when a timeline prints the end date first (`app/postprocess/dates.py`) — *Claude*
