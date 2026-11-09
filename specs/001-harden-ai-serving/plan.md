# Implementation Plan: Hardening AI CV Extraction Serving

**Branch**: `001-harden-ai-serving` (spec dir only, no git branch) | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-harden-ai-serving/spec.md`

## Summary

Make `ai-service` safe and predictable without changing the model or prompt: stop logging CV content, return generic 500s with a request id, auto-discover the GGUF file actually present (`merged_model/model.gguf`) and report fallback reasons, enforce a token budget (prompt + `MAX_NEW_TOKENS` ≤ context) with HTTP 413 instead of overflow/truncation, serialise inference behind a lock with a 30 s wait limit (HTTP 503), and add a pytest suite that stubs the model.

## Technical Context

**Language/Version**: Python 3.14 (existing `ai-service/.venv`); code stays compatible with ≥3.10 (README)
**Primary Dependencies**: FastAPI, Pydantic, transformers + PEFT, llama-cpp-python (declared, **not installed** in venv), json-repair
**Storage**: N/A (model files on disk only)
**Testing**: pytest + FastAPI `TestClient` (httpx) — new dev deps in `ai-service/requirements-dev.txt`
**Target Platform**: Linux server / Colab T4, single GPU
**Project Type**: web-service (one of three components: backend, frontend, ai-service)
**Performance Goals**: No regression in per-request latency; quantised engine must actually be used (≈5× faster than fallback)
**Constraints**: No CV content in logs/errors (constitution IV); success response shape unchanged (II); backend Feign read timeout 60 s (default)
**Scale/Scope**: ~8 files in `ai-service/app`, new `ai-service/tests/`, README

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Minimal Scope | PASS | Only `ai-service`; no prompt/model/postprocess changes; `@app.on_event` deprecation left as-is |
| II. Explicit Contracts | PASS (documented change) | Additive error statuses 413, 503-busy; 500 body still `{"detail": str}`. Documented in [contracts/extract-cv.md](contracts/extract-cv.md) and README. Backend maps all non-2xx Feign errors to 500 → no backend change required |
| III. Proportionate Verification | PASS | New pytest suite; manual smoke of GGUF load when runtime installed |
| IV. CV Data Security | PASS (this feature's purpose) | Tests use synthetic CVs only |
| V. Maintainable Implementation | PASS | Small modules (`core/errors.py`), config via env |

Post-design re-check: PASS (no new violations).

## Project Structure

### Documentation (this feature)

```text
specs/001-harden-ai-serving/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/extract-cv.md
├── checklists/requirements.md
└── tasks.md            # /speckit.tasks
```

### Source Code (repository root)

```text
ai-service/
├── app/
│   ├── core/config.py        # + LOG_CV_CONTENT, CONTEXT_TOKENS, QUEUE_WAIT_SECONDS
│   ├── core/errors.py        # NEW: InputTooLongError, ModelBusyError
│   ├── services/model_loader.py  # GGUF discovery, fallback_reason, context_tokens
│   ├── services/generator.py     # count tokens, budget check, lock; no truncation
│   └── api/routes.py         # no PII logs, request id, 413/503 mapping, health reason
├── tests/                    # NEW: conftest (stub model), test_*.py
├── requirements-dev.txt      # NEW: pytest, httpx
├── pytest.ini                # NEW (testpaths, pythonpath)
└── README.md                 # contract + model file rules + install notes
```

**Structure Decision**: Changes confined to `ai-service/`; backend and frontend untouched.

## Design

1. **Config** (`config.py`): `LOG_CV_CONTENT` (bool, default false), `CONTEXT_TOKENS` (default 8192; falls back to legacy `MAX_INPUT_TOKENS` env if only that is set), `QUEUE_WAIT_SECONDS` (default 30).
2. **GGUF discovery** (`model_loader.py`): `resolve_gguf_path(configured) -> (path | None, reason | None)`: configured path exists → use; else list `*.gguf` in its parent dir: exactly 1 → use; 0 → reason "no GGUF file"; >1 → reason "multiple GGUF files, set GGUF_MODEL_PATH". `Llama(n_ctx=CONTEXT_TOKENS)`. ImportError/load error → `state.fallback_reason = "<ExceptionType>: llama_cpp unavailable/load failed"` (type + short static text, no paths of user data). `state.context_tokens` set for both engines.
3. **Token budget** (`generator.py`): `count_prompt_tokens(prompt)` per engine (`llm.tokenize(..., special=True)` / `len(tokenizer(prompt).input_ids)`); if `n + MAX_NEW_TOKENS > state.context_tokens` → `InputTooLongError(n, state.context_tokens - MAX_NEW_TOKENS)`. Remove `truncation=True, max_length` in transformers path.
4. **Serialisation**: module-level `threading.Lock`; `acquire(timeout=QUEUE_WAIT_SECONDS)` else `ModelBusyError`; budget check + generation inside the lock.
5. **Routes**: request id `uuid4().hex[:12]`, returned in `X-Request-ID` header on every extract response. Map `InputTooLongError`→413, `ModelBusyError`→503, other → 500 `"Trích xuất CV thất bại (request_id=…)"`. Logging: lengths/tokens/durations only; raw output only if `LOG_CV_CONTENT`; failures log exception **type + traceback frames without message** unless `LOG_CV_CONTENT`. Startup warning when `LOG_CV_CONTENT` on. Health adds `fallback_reason` (only when set) and `context_tokens`.
6. **Tests**: `conftest.py` patches `app.main.load_model` to no-op and installs a fake engine in `state` (fake `llm` with `tokenize`/`__call__`), so no torch/model import. Log assertions via `caplog`.

## Subagent Assignment (per CLAUDE.md tiers)

| Task group | Tier / model | Reason |
|---|---|---|
| Setup (dev deps, pytest config, conftest), docs | 1 Free `opencode/glm-5.3-flash-free` | Mechanical |
| Config + errors, GGUF discovery, routes | 2 Gemini `agy gemini-3.8-flash-medium` | Moderate, multi-file but clear |
| Generator budget + lock | 2 Gemini `agy gemini-3.8-flash-high` | Concurrency/edge cases |
| Tests per story | 1 Free → 2 Gemini on failure | Clear acceptance |
| Escalation | 3 ChatGPT `openai/gpt-6.1-sol` → 4 Claude | After 1 failed fix |
| Review & verification | Claude (orchestrator) | Always |

## Complexity Tracking

No constitution violations to justify.

## Open Items Requiring User Action

- Installing `llama-cpp-python` with CUDA into `.venv` (Python 3.14 → likely source build, `CMAKE_ARGS="-DGGML_CUDA=on"`) changes the environment; done only with user approval (task T013). Code and tests do not depend on it.
