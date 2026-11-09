# Research: Hardening AI CV Extraction Serving

## R1. Why GGUF never loads
- **Finding**: `ai-service/merged_model/` contains `model.gguf` (1.1 GB) but default `GGUF_MODEL_PATH` is `./merged_model/model-qwen3-1.7b-q4_k_m.gguf`; additionally `llama-cpp-python` is listed in `requirements.txt` but not installed in `.venv` (Python 3.14).
- **Decision**: Auto-discover a single `*.gguf` in the configured directory; expose `fallback_reason` in `/health`; document install.
- **Alternatives**: Rename file (manual, fragile); change default name to `model.gguf` (breaks those following README name).

## R2. Over-budget inputs: reject vs truncate
- **Decision**: Reject with HTTP 413 when `prompt_tokens + MAX_NEW_TOKENS > context_tokens`.
- **Rationale**: Truncation silently drops CV sections → incomplete profiles; llama.cpp otherwise errors as generic 500. Measured prompts 1,844–2,507 tokens, so 8,192 context leaves ample room; 413 should be rare.
- **Alternatives**: Truncate CV text (silent data loss); chunking (scope of later features).

## R3. Context size default
- **Decision**: `CONTEXT_TOKENS=8192` for both engines (llama `n_ctx`, transformers budget).
- **Rationale**: Qwen3-1.7B supports 32k; KV cache at 8k for 1.7B is small (<1 GB fp16). Training used 4096 max_seq; quality beyond ~4k unverified, but the measured range stays under 4k anyway.

## R4. Concurrency
- **Decision**: Single `threading.Lock` with `acquire(timeout=30)`.
- **Rationale**: FastAPI runs sync endpoints in a threadpool; `llama_cpp.Llama` and HF `generate` on a shared model are not safe concurrently. 30 s < Feign default read timeout 60 s.
- **Alternatives**: async queue/worker (more code, no throughput gain on one GPU); multiple workers (multiplies GPU memory).

## R5. Logging without PII
- **Decision**: Log only lengths, token counts, durations, engine, request id. On failure log exception type + traceback frames (no message) unless `LOG_CV_CONTENT=true`.
- **Rationale**: Exception messages (e.g. json-repair, tokenizer) may embed fragments of model output.

## R6. Testing without model
- **Decision**: pytest + `TestClient`; patch `app.main.load_model`; fake engine object in `state`.
- **Rationale**: Heavy imports (torch/transformers/llama_cpp) are lazy inside functions, so tests stay fast and offline.
