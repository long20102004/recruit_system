# Feature Specification: Serving robustness for model v3

**Created**: 2026-11-05
**Status**: Approved (user: "Các phần nào bạn đề xuất cần thực hiện thì có thể implement ngay, không cần tôi duyệt")
**Input**: v3 evaluation on the 20-CV real test set ([../007-dataset-v3-real-layouts/baseline.md](../007-dataset-v3-real-layouts/baseline.md)).

## Evidence
| Finding | Measured |
|---|---|
| Degenerate output hits the 2,048-token cap | 3/20 real CVs on Colab, 2/7 on CPU GGUF; gold output for these CVs is 500–700 tokens; one CV repeats a bullet 23×, another writes one 2,800-char string |
| A capped output loses every field after the loop | e.g. 0/7 projects and 0/15 skills on one CV; `repeat_penalty=1.1` does not fix it |
| Skills recall of the model alone is low on real CVs | v3 skills F1 0.74; some CVs 7/26 |
| Model ∪ KB text scan raises skills recall | earlier measurement: recall 0.83, F1 0.71 vs 0.56 model alone |
| Empty / unparseable model output returned as HTTP 200 | 4/53 empty profiles on Colab GPU (json_repair returns `{}` or a list) |

## User Scenarios

### US1 — Loop guard (P1)
Generation stops as soon as the output degenerates: a single JSON string longer than `LOOP_MAX_STRING_CHARS` (default 1,200) or the same string value appearing `LOOP_MAX_REPEATS` (default 3) times. The partial JSON is repaired, the repeated values are dropped, and the response carries the flag `OUTPUT_TRUNCATED` (also when the token cap is reached). Saves the time spent generating the loop.

### US2 — `skills_detected` (P1)
Enrichment adds `skills_detected`: KB skills found either in the model's `skills` (linked) or by scanning the CV text for KB skill names/aliases, each `{"id", "name", "category", "source": "model"|"text"|"both"}`, in CV order. Additive field; `skills` and `skills_normalized` unchanged. Module 2 matching should use `skills_detected`.

### US3 — Unusable output is an error (P2)
If the model output cannot be parsed into a JSON object, or the object has no content (no personal info value and every list empty), the API returns **502** `"Model trả về kết quả rỗng hoặc không hợp lệ (request_id=…)"` instead of 200 with an empty profile. The backend Feign client already treats every non-2xx as a failure, so no backend change.

### US4 — Serve v3 by default (P2)
`PROMPT_VERSION` default becomes `v3` if the 20-CV evaluation with US1+US2 beats v2 on company, school and skills; v1/v2 stay selectable.

## Contract changes (`POST /api/v1/extract-cv`)
- Response `data`: new optional field `skills_detected` (list) and new flag code `OUTPUT_TRUNCATED` in `flags`. Backward compatible.
- Error behaviour: 502 for empty/unparseable model output (was 200 with an empty profile, or 500 when parsing raised).

## Amendment (2026-11-05, user: "module 2 sẽ tự match, module 1 chỉ cần trả về output tương đối từ cv")
- KB/KG enrichment is **off by default** (`KG_ENABLED=false`): the response holds only the CV fields (personal_info, objective, education, experience, personal_projects, skills, certificates, honours, languages). `skills_normalized`, `implied_skills`, `school_normalized`, `skills_detected` and `flags` appear only with `KG_ENABLED=true` (experiments / ablation).
- No `OUTPUT_TRUNCATED` flag: the loop guard still stops generation and salvages the JSON; truncation is logged (reason code only).
- Backend `CandidateProfile` drops the enrichment fields (unknown fields are ignored).
- Grounding post-processing stays on (it removes values not found in the CV; it adds no field).

## Success Criteria
- SC-001: On the 20 real CVs, no response spends more than ~1.3× the gold length in tokens on a loop; degenerate outputs are flagged.
- SC-002: `skills_detected` recall ≥ 0.80 on the 20 real CVs, precision ≥ 0.6.
- SC-003: No CV data in logs (counts and codes only); all existing ai-service tests pass.
