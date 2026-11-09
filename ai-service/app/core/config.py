import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

# Auto-load ai-service/.env before any os.getenv() call below is executed.
# The path is anchored to BASE_DIR so startup works from any cwd;
# override=False keeps real OS environment variables taking precedence.
load_dotenv(BASE_DIR / ".env", override=False)

BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "unsloth/Qwen3-1.7B")

# v4 is the default for the bundled LoRA adapter.
# v4 (feature 013) = prompt v3 + the model retrained on column-aware (layout) text.
# v5 (feature 014) = prompt v3 + the model retrained on dataset v5 (many short jobs, students, layout L15).
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v4").strip().lower()
if PROMPT_VERSION not in {"v1", "v2", "v3", "v4", "v5"}:
    raise ValueError("PROMPT_VERSION must be 'v1', 'v2', 'v3', 'v4' or 'v5'")

# Each prompt version has its own model file: the prompt and the weights must match.
DEFAULT_GGUF = {
    "v1": "./merged_model/model.gguf",
    "v2": "./merged_model/model-v2-q4_k_m.gguf",
    "v3": "./merged_model/model-v3-q4_k_m.gguf",
    "v4": "./merged_model/model-v4-q4_k_m.gguf",
    "v5": "./merged_model/model-v5-q4_k_m.gguf",
}
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", DEFAULT_GGUF[PROMPT_VERSION])

DEFAULT_LORA = {
    "v1": "./checkpoint-250",
    "v2": None,
    "v3": None,
    "v4": "./checkpoint-v4",
    "v5": None,
}
LORA_PATH = os.getenv("LORA_PATH", DEFAULT_LORA[PROMPT_VERSION])

# Engine selection: "transformers" (LoRA) or "llama_cpp" (GGUF)
# Default is "transformers" (LoRA)
MODEL_ENGINE = os.getenv("MODEL_ENGINE", "transformers").strip().lower()


MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "1500" if PROMPT_VERSION == "v1" else "2048"))
LOOP_MAX_STRING_CHARS = int(os.getenv("LOOP_MAX_STRING_CHARS", "2000"))
LOOP_MAX_REPEATS = int(os.getenv("LOOP_MAX_REPEATS", "3"))
CONTINUATION_ENABLED: bool = (
    os.getenv("CONTINUATION_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
)

MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "8192"))

CONTEXT_TOKENS: int = int(
    os.getenv("CONTEXT_TOKENS") or os.getenv("MAX_INPUT_TOKENS") or "8192"
)

QUEUE_WAIT_SECONDS: float = float(os.getenv("QUEUE_WAIT_SECONDS", "30"))

LOG_CV_CONTENT: bool = (
    os.getenv("LOG_CV_CONTENT", "").strip().lower() in {"1", "true", "yes", "on"}
)


def _resolve(p: str) -> str:
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(BASE_DIR, p))

POSTPROCESS_ENABLED: bool = (
    os.getenv("POSTPROCESS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
)

# KB/KG enrichment runs by default (KG_ENABLED=true) but its extra fields are hidden by default;
# see include=kg query param on POST /api/v1/extract-cv.
KG_ENABLED: bool = (
    os.getenv("KG_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
)

KB_DSN: str | None = os.getenv("KB_DSN") or None

KB_SEED_DIR: str = _resolve(os.getenv("KB_SEED_DIR", "./kb/seed"))

NEO4J_URI: str | None = os.getenv("NEO4J_URI") or None
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str | None = os.getenv("NEO4J_PASSWORD") or None
