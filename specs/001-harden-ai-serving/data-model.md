# Data Model: Hardening AI CV Extraction Serving

No persistent data. In-memory entities only:

- **ModelState** (`app/services/model_loader.py`): `engine` (`llama_cpp` | `transformers` | None), `llm`, `model`, `tokenizer`, `gguf_path_used`, **new** `context_tokens: int | None`, **new** `fallback_reason: str | None`.
- **InputTooLongError** (`app/core/errors.py`): `prompt_tokens: int`, `max_prompt_tokens: int`.
- **ModelBusyError** (`app/core/errors.py`): `waited_seconds: float`.
- **Settings** (`app/core/config.py`): `LOG_CV_CONTENT: bool = False`, `CONTEXT_TOKENS: int = 8192`, `QUEUE_WAIT_SECONDS: float = 30`, existing `MAX_NEW_TOKENS`, `GGUF_MODEL_PATH`, `LORA_PATH`, `BASE_MODEL_NAME`.
