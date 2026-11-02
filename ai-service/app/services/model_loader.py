import json
import os

from app.core.config import (
    BASE_MODEL_NAME,
    GGUF_MODEL_PATH,
    LORA_PATH,
    _resolve,
)
from app.core.logging import logger


class ModelState:
    def __init__(self):
        self.engine = None  # "llama_cpp" (GGUF merged, ưu tiên) | "transformers" (base + LoRA)
        self.llm = None
        self.tokenizer = None
        self.model = None
        self.gguf_path_used = None


state = ModelState()


def _adapter_base(lora_path: str) -> str | None:
    """Đọc base model thật từ adapter_config.json.

    Adapter train bằng Unsloth luôn ghi base ...-unsloth-bnb-4bit.
    Nạp đúng base này (strip suffix khi tải bản full) thì kích thước khớp
    và trọng số đúng; nạp sai base cùng kiến trúc thì chạy vẫn chạy nhưng
    output rác mà không báo lỗi.
    """
    cfg = os.path.join(_resolve(lora_path), "adapter_config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                name = json.load(f).get("base_model_name_or_path")
            if name:
                return name
        except Exception:
            pass
    return None


def _preload_cuda_libs():
    try:
        import ctypes
        import glob
        _cuda_dirs = [
            "/usr/local/cuda/lib64",
            "/usr/local/cuda-12/lib64",
            "/usr/local/cuda-12.4/lib64",
            "/usr/local/cuda-12.2/lib64",
            "/usr/local/cuda-12.1/lib64",
            "/usr/local/cuda-12.0/lib64",
            "/usr/lib/x86_64-linux-gnu",
        ]
        try:
            import site
            for _sp in site.getsitepackages():
                _cuda_dirs.extend(glob.glob(os.path.join(_sp, "nvidia", "*", "lib")))
        except Exception:
            pass
        for _d in _cuda_dirs:
            if os.path.isdir(_d):
                for _lib in ["libcudart.so.12", "libcudart.so", "libcublas.so.12", "libcublas.so"]:
                    _p = os.path.join(_d, _lib)
                    if os.path.exists(_p):
                        try:
                            ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                        except Exception:
                            pass
    except Exception as _ce:
        logger.debug(f"Preload CUDA libs note: {_ce}")


def load_model():
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel

    logger.info("=" * 70)
    logger.info("Loading CV Extraction Model")
    logger.info("=" * 70)

    # Ưu tiên 1: GGUF merged (standalone, không cần LoRA adapter)
    _gguf = _resolve(GGUF_MODEL_PATH)
    if os.path.exists(_gguf):
        try:
            _preload_cuda_libs()

            from llama_cpp import Llama

            logger.info(f"GGUF found: {_gguf}")
            logger.info("Loading GGUF (merged finetune, LoRA adapter KHÔNG cần thiết)...")
            state.llm = Llama(
                model_path=_gguf,
                n_ctx=4096,
                n_threads=6,
                n_gpu_layers=99,      # Offload 100% layers lên GPU
                verbose=True
            )
            state.engine = "llama_cpp"
            state.gguf_path_used = _gguf
            logger.info("=" * 70)
            logger.info("MODEL LOADED SUCCESSFULLY (llama.cpp GGUF)")
            logger.info("=" * 70)
            return
        except Exception:
            logger.exception("Nạp GGUF thất bại, fallback sang transformers...")

    # Ưu tiên 2: transformers base + LoRA (fallback, chậm hơn ~5 lần)
    lora_abs = _resolve(LORA_PATH)
    base_from_adapter = _adapter_base(LORA_PATH)
    base_name = BASE_MODEL_NAME
    if base_from_adapter and base_from_adapter != BASE_MODEL_NAME:
        logger.info(
            f"Adapter khai base '{base_from_adapter}' -> "
            f"dùng đúng base này thay vì default '{BASE_MODEL_NAME}'."
        )
        base_name = base_from_adapter
    base_name = base_name.replace("-unsloth-bnb-4bit", "").replace("-unsloth", "")

    logger.info(f"Base model : {base_name}")
    logger.info(f"LoRA path  : {lora_abs}")

    if not os.path.exists(lora_abs):
        raise RuntimeError(
            f"Không tìm thấy LoRA checkpoint: {lora_abs}"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    logger.info(f"Device : {device}")
    logger.info(f"Dtype  : {dtype}")

    logger.info("Loading tokenizer...")
    state.tokenizer = AutoTokenizer.from_pretrained(
        lora_abs,
        use_fast=True
    )

    logger.info("Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_name,
        torch_dtype=dtype,
        low_cpu_mem_usage=True
    )

    logger.info("Loading LoRA adapter...")
    state.model = PeftModel.from_pretrained(
        base_model,
        lora_abs
    )
    state.model.to(device)
    state.model.eval()
    state.engine = "transformers"

    logger.info("=" * 70)
    logger.info("MODEL LOADED SUCCESSFULLY (transformers + LoRA)")
    logger.info("=" * 70)
