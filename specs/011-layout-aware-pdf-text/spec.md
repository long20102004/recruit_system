# Feature Specification: Layout-aware PDF text (reading order) for the LLM path

**Created**: 2026-11-05 · **Status**: Clarified
**Input**: User: a two-column DevOps CV comes out with school = "CAO THANG TECHNICAL COLLEGE MI-JACK MANUFACTURING GLOBAL", company = "TOIEC", project mixed with Shopee bullets. Agreed solution: fix the text extraction, not the model; no template catalogue; keep v3 label conventions (skills one item each and normalised, end_date null for Present, certificates/languages as v3).

## Evidence
- `CvAnalysisService.extractTextFromPdf` (LLM path) uses `PDFTextStripper` + `setSortByPosition(true)`: every output line = left-column fragment + right-column fragment of the same y ("GPA: 7.8 03/2025 IT Engineer").
- The existing `PdfTextExtractor` (rule-based path) splits columns once with a fixed rule (top 15 % = header) and breaks some one-column CVs: on the 19 labelled test CVs, gold strings still contiguous: companies 100 % → 88 %, bullets 90 % → 83 %, schools 95 % → 89 % (CV 21: 7/7 → 1/7); better on 3 two-column CVs.
- All 4/20 real test CVs whose v3 output degenerated are two-column.

## Clarifications
- Template-independent geometry: recursive XY-cut on positioned text, no template list.
- Label conventions unchanged (no relabelling, no retraining in this feature).
- Real CVs never leave the machine; subagents work on synthetic PDFs only.

## Requirements
- FR-1: Positioned glyphs → lines (y clustering, tolerance from glyph height) → **segments** (a line split where the horizontal gap is large, relative to the line's font size).
- FR-2: Recursive XY-cut on segments: at each region, cut at the widest valid vertical gutter (white x-interval crossing the whole region) or the widest horizontal gap; recurse; leaf = segments in y then x order. Reading order: top → bottom, left → right.
- FR-3: A vertical cut is valid only when both sides are real text columns: each side has ≥ 3 segments and its median segment width is ≥ 18 % of the region width. Narrow side columns of dates / labels (timelines, right-aligned dates) are NOT columns: such rows stay together ("09/2018 NETWORK ADMINISTRATOR", "Company ..... 2020 – 2022").
- FR-4: The LLM path uses the layout-aware text behind `cv.pdf.text-mode` = `layout` | `legacy` (default decided by the measurement, see SC). `/api/v1/cv/extract-text` returns the same text the LLM receives. Rule-based path keeps working (same `ExtractionResult` API).
- FR-5: ai-service skill cleaning keeps "AWS (IAM, S3, EC2)" as "AWS", "IAM", "S3", "EC2" (never "AWS (IAM").

## Success Criteria
- SC-001: On the labelled real CVs (19 test + 31 train), gold strings contiguous in the new text ≥ legacy for one-column CVs (no regression) and higher on two-column CVs.
- SC-002: v3 on the two-column real CVs with the new text: company / school / project F1 higher than with legacy text; the user's DevOps CV matches the expected JSON on school, companies, titles, dates.
- SC-003: Backend tests (synthetic PDFs: header + 2 columns, 1 column with right-aligned dates, left timeline dates, 3 columns, 2 pages) and ai-service tests pass.
