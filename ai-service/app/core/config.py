import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "unsloth/Qwen3-1.7B")

LORA_PATH = os.getenv("LORA_PATH", "./checkpoint-250")

# v3 (feature 007/008) is the default model; v1 / v2 stay available with PROMPT_VERSION=v1 / v2.
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v3").strip().lower()
if PROMPT_VERSION not in {"v1", "v2", "v3"}:
    raise ValueError("PROMPT_VERSION must be 'v1', 'v2' or 'v3'")

# Each prompt version has its own model file: the prompt and the weights must match.
DEFAULT_GGUF = {
    "v1": "./merged_model/model.gguf",
    "v2": "./merged_model/model-v2-q4_k_m.gguf",
    "v3": "./merged_model/model-v3-q4_k_m.gguf",
}
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", DEFAULT_GGUF[PROMPT_VERSION])

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "1500" if PROMPT_VERSION == "v1" else "2048"))
LOOP_MAX_STRING_CHARS = int(os.getenv("LOOP_MAX_STRING_CHARS", "2000"))
LOOP_MAX_REPEATS = int(os.getenv("LOOP_MAX_REPEATS", "3"))

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

# KB/KG enrichment (skills_normalized, implied_skills, school_normalized, skills_detected, flags) is off by
# default: module 1 returns only what the CV says, module 2 does the matching. Kept for ablation / experiments.
KG_ENABLED: bool = (
    os.getenv("KG_ENABLED", "false").strip().lower() not in {"0", "false", "no", "off"}
)

KB_DSN: str | None = os.getenv("KB_DSN") or None

KB_SEED_DIR: str = _resolve(os.getenv("KB_SEED_DIR", "./kb/seed"))
