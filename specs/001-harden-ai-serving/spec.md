# Feature Specification: Hardening AI CV Extraction Serving

**Feature Branch**: `001-harden-ai-serving` (spec directory only; no git branch created)
**Created**: 2026-11-04
**Status**: Draft
**Input**: User description: "Feature 001 từ requirements.md — hardening ai-service: không log dữ liệu CV, không trả chi tiết lỗi nội bộ, kiểm soát ngân sách token so với context, tuần tự hoá inference, sửa việc nạp GGUF thất bại, bổ sung test."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CV data is not leaked through logs or error responses (Priority: P1)

As the system operator handling candidates' CVs, I need the extraction service to never write candidates' personal content (names, emails, phones, CV text, model output) to logs or return internal error details to callers, so that personal data stays confined to the request/response that legitimately carries it.

**Why this priority**: Constitution principle IV (CV Data Security) is mandatory; the current service logs full model output at the default level and returns raw exception messages.

**Independent Test**: Send a CV containing a known unique email/phone and force both a success and a failure; inspect captured logs and the error body — neither contains the CV's personal values or internal exception text.

**Acceptance Scenarios**:

1. **Given** default configuration, **When** a CV is extracted successfully, **Then** logs contain only non-identifying operational data (lengths, token counts, durations, engine) and no CV text or extracted values.
2. **Given** extraction fails internally, **When** the caller receives the error, **Then** the body contains a generic message and a request identifier, and no exception text, stack trace, or model output.
3. **Given** an operator explicitly enables a debug content-logging setting in a non-production environment, **When** a CV is processed, **Then** raw model output may be logged, and the service warns at startup that content logging is on.

---

### User Story 2 - Optimised model engine actually loads (Priority: P1)

As the operator, I need the service to load the quantised model file that is present in the model folder, and to report clearly which engine is active and why the preferred engine was not used, so that extraction runs at the expected speed instead of silently falling back to the ~5× slower engine.

**Why this priority**: The quantised model is present on disk but never used (configured filename does not match the actual file, and the runtime library is missing), which makes latency targets unreachable.

**Independent Test**: With exactly one quantised model file in the model folder and the runtime available, start the service and call the health endpoint: it reports the quantised engine and the file in use.

**Acceptance Scenarios**:

1. **Given** the configured model file path does not exist but the model folder contains exactly one quantised model file, **When** the service starts, **Then** it loads that file and logs which file was chosen.
2. **Given** the quantised model cannot be loaded (missing runtime or corrupt file), **When** the service starts, **Then** it falls back to the adapter engine and the health endpoint exposes the fallback reason (without personal data).
3. **Given** the folder contains several quantised files and no valid configured path, **When** the service starts, **Then** it does not guess; it reports the ambiguity and falls back.

---

### User Story 3 - Long CVs fail predictably instead of crashing (Priority: P2)

As the backend consuming the service, I need CVs whose prompt plus expected output exceed the model's context capacity to be rejected with a distinct, documented client error, rather than an opaque server error or silently truncated output.

**Why this priority**: Measured prompts are 1,844–2,507 tokens and output budget is 1,500, which is close to the current 4,096 context on the quantised engine; overflow currently surfaces as a generic 500.

**Independent Test**: Submit a synthetic CV large enough to exceed the budget; receive the documented "input too long" error with the measured and allowed token counts.

**Acceptance Scenarios**:

1. **Given** a CV whose prompt tokens + output budget ≤ context capacity, **When** submitted, **Then** it is processed normally.
2. **Given** a CV whose prompt tokens + output budget > context capacity, **When** submitted, **Then** the service responds with HTTP 413 and a message stating the prompt token count and the maximum allowed, without invoking generation.
3. **Given** either engine is active, **When** the budget check runs, **Then** it applies the same rule (no silent truncation on either engine).

---

### User Story 4 - Concurrent requests are safe (Priority: P2)

As the backend, I need simultaneous extraction requests to be processed safely one at a time against the single loaded model, so that concurrent calls neither crash the service nor mix outputs.

**Why this priority**: The endpoint runs in a thread pool sharing one non-thread-safe model instance.

**Independent Test**: Fire several concurrent requests with distinct CVs against a stubbed model that detects overlapping calls; no overlap occurs and each response matches its own input.

**Acceptance Scenarios**:

1. **Given** N concurrent requests, **When** they are processed, **Then** at most one generation runs at any moment and every request receives its own result.
2. **Given** a request has waited longer than the configured queue-wait limit, **When** the limit elapses, **Then** it receives HTTP 503 "busy, retry later" instead of waiting indefinitely.

---

### User Story 5 - Automated regression tests exist (Priority: P2)

As a developer, I need an automated test suite for the service that runs without downloading or loading the real model, so that the behaviours above stay correct.

**Independent Test**: Run the test command on a machine without the model; all tests pass in under one minute.

**Acceptance Scenarios**:

1. **Given** a clean checkout with dev dependencies installed, **When** the test command runs, **Then** tests cover: input validation (400), model-not-loaded (503), token budget (413), busy (503), generic 500 body, no-PII logging, JSON extraction utility, model-file discovery.

### Edge Cases

- `cv_text` that is only whitespace → 400 (existing behaviour preserved).
- Model folder contains a `.gguf` file plus `.gitkeep` → only `.gguf` files are candidates.
- Configured model path explicitly set and present → always used, discovery skipped.
- Token counting itself fails → treated as internal error (generic 500), not as success.
- Debug content logging enabled → only affects logs, never response bodies.
- Health check while model is loading/failed → 503 as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST NOT write CV text, extracted field values, or raw model output to logs under default configuration.
- **FR-002**: The service MUST provide an opt-in, default-off setting to log raw model output for debugging, and MUST emit a warning at startup when it is enabled.
- **FR-003**: Internal extraction failures MUST return HTTP 500 with a generic message and a per-request identifier; the identifier MUST also appear in the server log entry for that failure (with exception type and stack trace, but no personal content).
- **FR-004**: When the configured quantised model path does not exist, the service MUST look in the model folder and use the single quantised model file found; with zero or multiple candidates it MUST NOT guess.
- **FR-005**: The health endpoint MUST report the active engine, the model identifier in use, and, if the preferred engine was not used, a short non-personal reason.
- **FR-006**: The quantised engine's runtime dependency MUST be declared so a standard install makes the preferred engine loadable; the README MUST describe the actual model file location/name rules.
- **FR-007**: The context capacity of the quantised engine MUST be configurable, with a default large enough for the measured prompt range plus the output budget (default 8,192 tokens).
- **FR-008**: Before generation, the service MUST compute prompt tokens and reject with HTTP 413 when prompt tokens + output budget exceed the active engine's context capacity; this rule MUST replace silent truncation on the adapter engine.
- **FR-009**: Generation MUST be serialised so that at most one inference runs at a time per loaded model.
- **FR-010**: A request waiting for the model longer than a configurable limit (default 30 s, below the backend client's default 60 s read timeout) MUST receive HTTP 503 with a retry message.
- **FR-011**: Existing success response shape (`{"data": {...}}`), 400 and 503-not-loaded behaviours MUST remain unchanged.
- **FR-012**: The new error statuses (413, 503-busy) and the generic 500 body MUST be documented in the service README as part of the `POST /api/v1/extract-cv` contract.
- **FR-013**: An automated test suite MUST run without the real model (model calls stubbed) and cover FR-001…FR-011.

### Key Entities

- **Extraction request**: CV text submitted by the backend; carries personal data; lifetime = one request.
- **Engine state**: which engine is active, the model identifier in use, fallback reason, context capacity.
- **Error response**: status, generic message, request identifier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test run processing CVs with known unique personal values, 0 occurrences of those values appear in captured logs under default configuration.
- **SC-002**: With the provided model file in the model folder, the service starts on the quantised engine on the first attempt, with no manual renaming or path configuration.
- **SC-003**: 100% of inputs exceeding the token budget return 413; 0 return 500.
- **SC-004**: Under 5 concurrent requests, 0 crashes and 0 mismatched responses.
- **SC-005**: The automated suite passes in under 60 seconds without network or model files.
- **SC-006**: Existing backend client continues to work unchanged for valid CVs (same success shape).

## Assumptions

- Over-budget inputs are rejected (413), not truncated: truncated CVs would yield incomplete profiles silently, which is worse for downstream modules. Backend currently maps any non-2xx to an error, so adding 413 is backward compatible for callers; the backend may later present a specific message (out of scope).
- Default context capacity 8,192 is within the model's supported range and the memory cost on a 1.7B model is acceptable on the target T4/local GPU.
- Serialised processing (one at a time) is acceptable given a single GPU; throughput scaling (multiple workers/batching) is out of scope.
- The backend's HTTP client uses its default read timeout (60 s); queue wait + generation must normally fit inside it. Tuning backend timeouts is out of scope.
- Adding test-only dependencies (test runner, HTTP test client) in a separate dev requirements file is acceptable.
- Retraining, prompt changes, post-processing (feature 002), and performance targets of 1–2 s are out of scope.
