import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "unsloth/Qwen3-1.7B")

LORA_PATH = os.getenv("LORA_PATH", "./checkpoint-250")

GGUF_MODEL_PATH = os.getenv(
    "GGUF_MODEL_PATH",
    "./merged_model/model-qwen3-1.7b-q4_k_m.gguf"
)

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "1500"))

MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "8192"))


def _resolve(p: str) -> str:
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(BASE_DIR, p))
