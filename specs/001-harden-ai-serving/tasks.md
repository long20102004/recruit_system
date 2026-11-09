# Tasks: Hardening AI CV Extraction Serving

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [contracts/extract-cv.md](contracts/extract-cv.md)
**Tests**: Included (FR-013). All paths relative to repo root. `[P]` = parallelisable (different files, no dependency). Subagent column follows CLAUDE.md tiers; Claude reviews every task before marking `[x]`.

## Phase 1: Setup

- [x] T001 [P] Create `ai-service/requirements-dev.txt` (only `pytest`, `httpx`; runtime deps stay in `requirements.txt`) and `ai-service/pytest.ini` (`testpaths = tests`, `pythonpath = .`) — *Free glm-5.3*
- [x] T002 Install dev deps into `ai-service/.venv` (`pip install -r requirements-dev.txt`) — *Claude*

## Phase 2: Foundational (blocks all stories)

- [x] T003 [P] Add `LOG_CV_CONTENT`, `CONTEXT_TOKENS` (legacy `MAX_INPUT_TOKENS` fallback), `QUEUE_WAIT_SECONDS` to `ai-service/app/core/config.py` — *Gemini medium*
- [x] T004 [P] Create `ai-service/app/core/errors.py` with `InputTooLongError(prompt_tokens, max_prompt_tokens)`, `ModelBusyError(waited_seconds)` — *Gemini medium (same dispatch as T003)*
- [x] T005 Create `ai-service/tests/conftest.py`: patch `app.main.load_model` to no-op, fixture `fake_engine` installing a fake `llm` (`tokenize`, `__call__` returning JSON text) into `state` with `engine="llama_cpp"`, `context_tokens`, and `client` fixture (`TestClient(app)`); reset `state` after each test — *Free glm-5.3* (depends T003, T004)

**Checkpoint**: `pytest` collects with 0 tests failing.

## Phase 3: US1 — No CV data in logs/errors (P1) 🎯 MVP

- [x] T006 [US1] In `ai-service/app/api/routes.py`: request id (`uuid4().hex[:12]`, `X-Request-ID` header), remove raw-output logging unless `LOG_CV_CONTENT`, generic 500 detail with request id, failure log = exception type + traceback frames without message (full `exc_info` only if `LOG_CV_CONTENT`); also map `InputTooLongError`→413 and `ModelBusyError`→503 per contract (single owner of routes.py) — *Gemini medium*
- [x] T007 [US1] Startup warning when `LOG_CV_CONTENT` is on in `ai-service/app/main.py` — *Gemini medium (with T006)*
- [x] T008 [P] [US1] `ai-service/tests/test_privacy.py`: synthetic CV with unique email/phone → success and forced failure; assert values absent from `caplog` and 500 body; `X-Request-ID` present; 400 for whitespace — *Free glm-5.3*

## Phase 4: US2 — Quantised engine loads (P1)

- [x] T009 [US2] In `ai-service/app/services/model_loader.py`: `resolve_gguf_path(configured) -> (path|None, reason|None)`; `Llama(n_ctx=CONTEXT_TOKENS)`; set `state.context_tokens` (both engines) and `state.fallback_reason` (exception type + static text) — *Gemini medium*
- [x] T010 [US2] `/health` in `ai-service/app/api/routes.py`: add `context_tokens`, `fallback_reason` (only when set) — *Gemini medium (after T006, same file)*
- [x] T011 [P] [US2] `ai-service/tests/test_model_discovery.py`: tmp dirs with configured file / 1 gguf + .gitkeep / 0 / 2 files; health includes `fallback_reason` — *Free glm-5.3*

## Phase 5: US3 + US4 — Token budget & serialisation (P2)

- [x] T012 [US3][US4] In `ai-service/app/services/generator.py`: `count_prompt_tokens` per engine; module `threading.Lock` with `acquire(timeout=QUEUE_WAIT_SECONDS)` → `ModelBusyError`; inside lock: budget check (`n + MAX_NEW_TOKENS > state.context_tokens` → `InputTooLongError`) then generate; remove transformers `truncation/max_length` — *Gemini high*
- [x] T013 [US2] (environment, **needs user approval**) Install `llama-cpp-python` with CUDA into `ai-service/.venv`; smoke `/health` shows `engine=llama_cpp` — *Claude*
- [x] T014 [P] [US3] `ai-service/tests/test_token_budget.py`: under/over budget → 200/413 with counts, generation not called on 413 — *Free glm-5.3*
- [x] T015 [P] [US4] `ai-service/tests/test_concurrency.py`: fake `llm` detecting overlap, 5 threads → no overlap, each response matches input; tiny `QUEUE_WAIT_SECONDS` + held lock → 503 — *Free glm-5.3*

## Phase 6: US5 + Polish

- [x] T016 [P] `ai-service/tests/test_json_parse.py`: `extract_json` fenced/think/garbage/invalid cases — *Free glm-5.3*
- [x] T017 [P] Update `ai-service/README.md`: new env vars, GGUF file rules (auto-discovery), dev/test commands, contract table from `contracts/extract-cv.md` — *Free glm-5.3*
- [x] T018 Full verification: `pytest -q` (< 60 s), grep logs for synthetic PII, review diff vs constitution, run quickstart smoke if model available — *Claude*

## Dependencies & Execution Order

```text
T001 → T002 ─┐
T003 ∥ T004 ─┴→ T005 → { T006→T007→T010 , T009 , T012 } → tests T008 ∥ T011 ∥ T014 ∥ T015 ∥ T016 ∥ T017 → T018
T013 independent (after user approval)
```

- Dispatch batch A (parallel): T001, T003+T004.
- Batch B: T005. Batch C (parallel, different files): T006+T007 (routes/main), T009 (model_loader), T012 (generator). Then T010 (routes, sequential after T006).
- Batch D (parallel, separate test files): T008, T011, T014, T015, T016, T017.
- MVP = Phases 1–3 (US1).
