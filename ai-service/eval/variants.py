"""Evaluation variants for ablation studies."""

from __future__ import annotations

from typing import Any, Callable

from app.postprocess import postprocess

VariantFn = Callable[[Any, str], Any]

VARIANTS: dict[str, VariantFn] = {
    "A": lambda data, cv: data,
    "B": lambda data, cv: postprocess(data, cv)[0] if isinstance(data, dict) else data,
}
