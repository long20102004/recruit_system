# Contract: AI Service (after feature 001)

## POST /api/v1/extract-cv

Request: `{"cv_text": "<string>"}`
Response headers: `X-Request-ID: <12 hex>` (new, all responses from this endpoint)

| Status | When | Body | Change |
|---|---|---|---|
| 200 | Success | `{"data": {...CandidateProfile...}}` | unchanged |
| 400 | `cv_text` empty/whitespace | `{"detail": "cv_text không được rỗng"}` | unchanged |
| 413 | prompt tokens + output budget > context | `{"detail": "CV quá dài: <n> token, tối đa <max> token"}` | **new** |
| 503 | model not loaded | `{"detail": "Model chưa được load"}` | unchanged |
| 503 | model busy > `QUEUE_WAIT_SECONDS` | `{"detail": "Service đang bận, vui lòng thử lại sau"}` | **new** |
| 500 | internal failure | `{"detail": "Trích xuất CV thất bại (request_id=<id>)"}` | **changed**: no exception text |

Consumer impact: backend `AiServiceClient` (Feign) treats all non-2xx as `FeignException` → its own 500. No backend change required; distinguishing 413/503 in backend is a possible follow-up.

## GET /health

Unchanged fields: `status`, `engine`, `model`, and `lora`, `device` (transformers only).
New fields: `context_tokens` (int, always), `fallback_reason` (string, only when the GGUF engine was not used).
