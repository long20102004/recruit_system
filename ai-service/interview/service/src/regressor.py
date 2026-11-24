"""Load a fine-tuned regression BERT and score one answer."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .finetune_bert import build_text
from .io_utils import ROOT

__all__ = ["model_dir", "load_regressor", "predict_regression", "model_version"]


def model_dir() -> Path:
    configured = os.getenv("HIRELENS_FINETUNE_DIR")
    if configured:
        return Path(configured)
    return ROOT / "output" / "bert_finetuned_self" / "model"


def model_version() -> str:
    return os.getenv("HIRELENS_FINETUNE_VERSION", "bert-finetuned-self")


@lru_cache(maxsize=1)
def load_regressor():
    path = model_dir()
    if not (path / "config.json").exists():
        raise FileNotFoundError(
            f"Chưa có mô hình fine-tune tại {path}. "
            "Chạy: python -m src.finetune_bert --scenario self"
        )
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path)
    model.eval()
    device = os.getenv("HIRELENS_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return tokenizer, model, device


def predict_regression(question: str, answer: str, reference: str | None) -> float:
    import torch

    tokenizer, model, device = load_regressor()
    text = build_text(question or "", answer or "", reference)
    encoded = tokenizer(text, truncation=True, padding=True, max_length=256, return_tensors="pt")
    encoded = {key: value.to(device) for key, value in encoded.items()}
    with torch.no_grad():
        logits = model(**encoded).logits
    score = float(logits.reshape(-1)[0].item())
    return max(0.0, min(10.0, score))
